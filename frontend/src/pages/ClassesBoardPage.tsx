import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Select,
  Spinner,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  DndContext,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import { useDraggable } from "@dnd-kit/core";

import BoardToolbar from "../components/classes/BoardToolbar";
import ClassColumn from "../components/classes/ClassColumn";
import StudentCard from "../components/classes/StudentCard";
import {
  assignStudentToClass,
  fetchClassStudents,
  fetchSchoolClasses,
  unassignStudentFromClass,
  type StudentItem,
} from "../services/classesBoard";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/apiClient";

// Storage key (tu app ya usa "school_id")
const SCHOOL_ID_KEY = "school_id";
const SCHOOL_NAME_KEY = "school_name";

function getSchoolId(): string {
  return localStorage.getItem(SCHOOL_ID_KEY) || "";
}

function getSchoolName(): string {
  return localStorage.getItem(SCHOOL_NAME_KEY) || "";
}

function setSchoolId(id: string) {
  localStorage.setItem(SCHOOL_ID_KEY, id);
}

function clearSchoolId() {
  localStorage.removeItem(SCHOOL_ID_KEY);
}

type BoardClass = {
  id: string;
  name: string;
  students: StudentItem[];
};

type SchoolItem = {
  id: string;
  name: string;
};

// Helpers dnd
function membershipId(studentId: string, fromClassId: string) {
  return `${studentId}::${fromClassId}`;
}

function parseMembershipId(id: string) {
  const [studentId, fromClassId] = id.split("::");
  return { studentId, fromClassId };
}

function DraggableStudentCard(props: {
  student: StudentItem;
  fromClassId: string;
  showHint?: boolean;
}) {
  const id = membershipId(props.student.id, props.fromClassId);

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id,
  });

  return (
    <Box
      ref={setNodeRef}
      style={{
        transform: transform
          ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
          : undefined,
        opacity: isDragging ? 0.2 : 1,
        zIndex: isDragging ? 1 : "auto",
      }}
      {...listeners}
      {...attributes}
    >
      <StudentCard student={props.student} showHint={props.showHint} />
    </Box>
  );
}

export default function ClassesBoardPage() {
  const toast = useToast();
  const { me } = useAuth();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [mode, setMode] = useState<"add" | "move">("add");
  const [search, setSearch] = useState("");

  const [classes, setClasses] = useState<BoardClass[]>([]);
  const [activeMembership, setActiveMembership] = useState<{
    studentId: string;
    fromClassId: string;
    student: StudentItem;
  } | null>(null);

  // school selection flow (platform_admin)
  const [schoolId, setSchoolIdState] = useState<string>(getSchoolId());
  const [schools, setSchools] = useState<SchoolItem[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<string>("");
  const [loadingSchools, setLoadingSchools] = useState(false);

  const isPlatformAdmin = me?.role === "platform_admin";
  const isSchoolScoped = me?.role === "school_admin" || me?.role === "teacher";
  const [schoolName, setSchoolName] = useState<string>(getSchoolName());

  // 1) Al entrar, lee schoolId de localStorage (por si cambió en otra tab)
  useEffect(() => {
    setSchoolIdState(getSchoolId());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  // 2) Si platform_admin y no hay schoolId => cargar lista de escuelas para selector
  useEffect(() => {
    (async () => {
      if (!isPlatformAdmin) return;
      if (schoolId) return;

      try {
        setLoadingSchools(true);

        // Ajusta este endpoint si el tuyo es distinto:
        // ejemplos comunes: /v1/schools, /api/v1/schools, etc.
        const data = await api<any>("/v1/schools", { auth: true });

        // Intento tolerante: acepta {items:[...]} o array directo
        const list: SchoolItem[] = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
            ? data.items
            : [];

        // Normaliza campos si vienen diferentes
        const normalized = list
          .map((s: any) => ({
            id: String(s.id ?? s.school_id ?? s._id ?? ""),
            name: String(s.name ?? s.school_name ?? "Escuela"),
          }))
          .filter((s) => s.id);

        normalized.sort((a, b) => a.name.localeCompare(b.name, "es"));

        setSchools(normalized);
      } catch (e: any) {
        setSchools([]);
        toast({
          status: "error",
          title: "No pude cargar escuelas",
          description: e?.message || "Revisa el endpoint /v1/schools y permisos.",
        });
      } finally {
        setLoadingSchools(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlatformAdmin, schoolId]);

  async function loadBoard(sid: string) {
    const cls = await fetchSchoolClasses(sid);

    const results = await Promise.all(
      cls.map(async (c) => {
        const students = await fetchClassStudents(c.id);
        return { id: c.id, name: c.name, students };
      })
    );

    results.sort((a, b) => a.name.localeCompare(b.name, "es"));
    setClasses(results);
  }

  // 3) Cargar board cuando ya haya schoolId
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);

        const sid = schoolId;

        if (!sid) {
          // platform_admin: aquí NO es error, es "elige escuela"
          if (isPlatformAdmin) {
            setClasses([]);
            return;
          }

          // school_admin/teacher: en tu implementación actual sí es problema
          if (isSchoolScoped) {
            toast({
              status: "error",
              title: "Falta school_id",
              description:
                "No encontré school_id en localStorage. Para school_admin/teacher debe venir en login o en /me.",
            });
            setClasses([]);
            return;
          }

          // otros roles
          toast({
            status: "error",
            title: "Falta school_id",
            description: "No se puede cargar el tablero sin school_id.",
          });
          setClasses([]);
          return;
        }

        await loadBoard(sid);
      } catch (e: any) {
        toast({
          status: "error",
          title: "Error cargando tablero",
          description: e?.message || "Error",
        });
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schoolId, me?.role]);

  async function refresh() {
    try {
      setRefreshing(true);

      if (!schoolId) {
        if (isPlatformAdmin) return; // no-op, aún no hay escuela elegida
        toast({
          status: "error",
          title: "Falta school_id",
          description: "No encontré school_id para refrescar.",
        });
        return;
      }

      await loadBoard(schoolId);
    } catch (e: any) {
      toast({
        status: "error",
        title: "Error refrescando",
        description: e?.message || "Error",
      });
    } finally {
      setRefreshing(false);
    }
  }

  const filteredClasses = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return classes;

    return classes.map((c) => ({
      ...c,
      students: c.students.filter((s) =>
        (s.full_name || "").toLowerCase().includes(q)
      ),
    }));
  }, [classes, search]);

  function onDragStart(ev: DragStartEvent) {
    const id = String(ev.active.id);
    if (!id.includes("::")) return;

    const { studentId, fromClassId } = parseMembershipId(id);

    const fromClass = classes.find((c) => c.id === fromClassId);
    const student = fromClass?.students.find((s) => s.id === studentId);

    if (!student) return;

    setActiveMembership({
      studentId,
      fromClassId,
      student,
    });
  }

  function onDragCancel() {
    setActiveMembership(null);
  }

  function optimisticMoveOrAdd(params: {
    studentId: string;
    fromClassId: string;
    toClassId: string;
    mode: "add" | "move";
  }) {
    setClasses((prev) => {
      const next = prev.map((c) => ({ ...c, students: [...c.students] }));

      const fromCol = next.find((c) => c.id === params.fromClassId);
      const toCol = next.find((c) => c.id === params.toClassId);
      if (!fromCol || !toCol) return prev;

      const student = fromCol.students.find((s) => s.id === params.studentId);
      if (!student) return prev;

      const alreadyInTarget = toCol.students.some((s) => s.id === params.studentId);
      if (!alreadyInTarget) {
        toCol.students.unshift(student);
      }

      if (params.mode === "move") {
        fromCol.students = fromCol.students.filter((s) => s.id !== params.studentId);
      }

      return next;
    });
  }

  function rollback() {
    refresh();
  }

  async function onDragEnd(ev: DragEndEvent) {
    setActiveMembership(null);

    const overId = ev.over?.id ? String(ev.over.id) : null;
    const activeId = String(ev.active.id);

    if (!overId) return;
    if (!activeId.includes("::")) return;

    const { studentId, fromClassId } = parseMembershipId(activeId);
    const toClassId = overId;

    if (fromClassId === toClassId) return;

    const targetHas = classes
      .find((c) => c.id === toClassId)
      ?.students.some((s) => s.id === studentId);

    if (mode === "add" && targetHas) {
      toast({
        status: "info",
        title: "Ya está inscrito",
        description: "Este alumno ya pertenece a esa clase.",
      });
      return;
    }

    optimisticMoveOrAdd({ studentId, fromClassId, toClassId, mode });

    try {
      if (mode === "move") {
        await unassignStudentFromClass(fromClassId, studentId);
        await assignStudentToClass(toClassId, studentId);
      } else {
        await assignStudentToClass(toClassId, studentId);
      }

      toast({
        status: "success",
        title: mode === "move" ? "Alumno movido" : "Alumno inscrito",
        description:
          mode === "move"
            ? "Se actualizó la inscripción."
            : "Se agregó a una nueva clase sin salirse de la anterior.",
      });
    } catch (e: any) {
      rollback();
      toast({
        status: "error",
        title: "No se pudo actualizar",
        description: e?.body?.detail || e?.message || "Error",
      });
    }
  }

  // --- UI: Selector de escuela para platform_admin ---
  if (!loading && isPlatformAdmin && !schoolId) {
    return (
      <Box p={{ base: 4, md: 8 }}>
        <VStack align="stretch" spacing={4} maxW="520px">
          <Heading size="lg">Class Manager</Heading>
          <Text color="blackAlpha.700">
            Eres <b>platform_admin</b>. Selecciona la escuela para cargar el tablero.
          </Text>

          {loadingSchools ? (
            <HStack spacing={3}>
              <Spinner />
              <Text>Cargando escuelas…</Text>
            </HStack>
          ) : schools.length === 0 ? (
            <Text color="red.500">
              No hay escuelas para seleccionar (o falló el endpoint). Revisa permisos o
              el endpoint <b>/v1/schools</b>.
            </Text>
          ) : (
            <>
              <Select
                placeholder="Elige una escuela…"
                value={selectedSchool}
                onChange={(e) => setSelectedSchool(e.target.value)}
              >
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>

              <Button
                colorScheme="blue"
                isDisabled={!selectedSchool}
                onClick={() => {
                  const school = schools.find((s) => s.id === selectedSchool);
                  if (school) {
                    setSchoolId(school.id);
                    setSchoolIdState(school.id);
                    setSchoolName(school.name);
                  }
                  toast({
                    status: "success",
                    title: "Escuela seleccionada",
                    description: "Cargando tablero…",
                  });
                }}
              >
                Entrar
              </Button>
            </>
          )}
        </VStack>
      </Box>
    );
  }

  // Loading normal
  if (loading) {
    return (
      <Flex minH="70vh" align="center" justify="center">
        <HStack spacing={3}>
          <Spinner />
          <Text>Cargando tablero…</Text>
        </HStack>
      </Flex>
    );
  }

  return (
    <Box p={{ base: 4, md: 8 }}>
      <VStack align="stretch" spacing={5}>
        <Box>
          <HStack justify="space-between" align="flex-start" wrap="wrap" gap={3}>
            <Box>
              <Heading size="lg" mb={1}>
                Classes Board
              </Heading>
              <Text color="blackAlpha.700">
                Arrastra alumnos entre columnas. Modo <b>Agregar</b> inscribe sin quitar;
                modo <b>Mover</b> cambia de clase.
              </Text>
            </Box>

            {/* platform_admin: muestra escuela activa y botón cambiar */}
            {isPlatformAdmin && schoolId && (
              <HStack spacing={3}>
                <Badge colorScheme="purple" borderRadius="full" px={3} py={1}>
                  School: {schoolName || schoolId}
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    clearSchoolId();
                    setSchoolName("");
                    setSchoolIdState("");
                    setSelectedSchool("");
                    setSchools([]);
                    toast({
                      status: "info",
                      title: "Selecciona otra escuela",
                      description: "Elige una escuela para cargar el tablero.",
                    });
                  }}
                >
                  Cambiar escuela
                </Button>
              </HStack>
            )}
          </HStack>
        </Box>

        <BoardToolbar
          search={search}
          onSearch={setSearch}
          mode={mode}
          onMode={setMode}
          onRefresh={refresh}
          isRefreshing={refreshing}
        />

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
          onDragCancel={onDragCancel}
        >
          <Box
            borderRadius="2xl"
            bg="blackAlpha.50"
            p={4}
            borderWidth="1px"
            borderColor="blackAlpha.100"
          >
            <Flex gap={5} align="flex-start" wrap="nowrap" overflowX="auto" pb={2}>
              {filteredClasses.map((c) => (
                <ClassColumn
                  key={c.id}
                  classId={c.id}
                  name={c.name}
                  count={c.students.length}
                >
                  {c.students.map((s) => (
                    <DraggableStudentCard
                      key={membershipId(s.id, c.id)}
                      student={s}
                      fromClassId={c.id}
                      showHint={false}
                    />
                  ))}
                </ClassColumn>
              ))}
            </Flex>
          </Box>

          <DragOverlay>
            {activeMembership ? (
              <Box
                w="100%"
                maxW="280px"
                boxShadow="2xl"
                borderRadius="xl"
                zIndex={9999}
                pointerEvents="none"
              >
                <StudentCard student={activeMembership.student} showHint={false} />
              </Box>
            ) : null}
          </DragOverlay>
        </DndContext>
      </VStack>
    </Box>
  );
}