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
  useColorModeValue,
} from "@chakra-ui/react";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  const toast = useToast();
  const { me } = useAuth();
  
  const panelBg = useColorModeValue("#ffffff", "gray.800");
  const headingColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textColor = useColorModeValue("#434654", "gray.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryHover = useColorModeValue("#0049ca", "blue.400");
  const inputBg = useColorModeValue("#f8f9fa", "whiteAlpha.50");
  const inputBorder = useColorModeValue("rgba(195, 197, 215, 0.15)", "whiteAlpha.100");
  const inputFocusBorder = useColorModeValue("rgba(0, 53, 151, 0.3)", "blue.300");
  const badgeBg = useColorModeValue("#e8edff", "whiteAlpha.200");
  const btnOutlineBorder = useColorModeValue("rgba(195, 197, 215, 0.4)", "whiteAlpha.300");
  const btnOutlineHover = useColorModeValue("#f3f4f5", "whiteAlpha.100");
  const scrollbarThumb = useColorModeValue("rgba(0, 53, 151, 0.15)", "whiteAlpha.300");
  const scrollbarThumbHover = useColorModeValue("rgba(0, 53, 151, 0.3)", "whiteAlpha.400");

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
          title: t("classes_board_page.toast.error_loading_schools_title"),
          description: e?.message || t("classes_board_page.toast.error_loading_schools_desc"),
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
              title: t("classes_board_page.toast.missing_school_id_title"),
              description: t("classes_board_page.toast.missing_school_id_teacher_desc"),
            });
            setClasses([]);
            return;
          }

          // otros roles
          toast({
            status: "error",
            title: t("classes_board_page.toast.missing_school_id_title"),
            description: t("classes_board_page.toast.missing_school_id_desc"),
          });
          setClasses([]);
          return;
        }

        await loadBoard(sid);
      } catch (e: any) {
        toast({
          status: "error",
          title: t("classes_board_page.toast.error_loading_board_title"),
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
          title: t("classes_board_page.toast.missing_school_id_title"),
          description: t("classes_board_page.toast.missing_refresh_id_desc"),
        });
        return;
      }

      await loadBoard(schoolId);
    } catch (e: any) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.error_refreshing_title"),
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
        title: t("classes_board_page.toast.enrolled_title"),
        description: t("classes_board_page.toast.enrolled_desc"),
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
        title: mode === "move" ? t("classes_board_page.toast.moved_title") : t("classes_board_page.toast.enrolled_success_title"),
        description:
          mode === "move"
            ? t("classes_board_page.toast.moved_desc")
            : t("classes_board_page.toast.enrolled_success_desc"),
      });
    } catch (e: any) {
      rollback();
      toast({
        status: "error",
        title: t("classes_board_page.toast.update_error_title"),
        description: e?.body?.detail || e?.message || "Error",
      });
    }
  }

  // --- UI: Selector de escuela para platform_admin ---
  if (!loading && isPlatformAdmin && !schoolId) {
    return (
      <Box px={{ base: 4, md: 8 }} py={{ base: 6, md: 8 }}>
        <VStack align="stretch" spacing={6} maxW="520px" bg={panelBg} p={8} borderRadius="2rem" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)">
          <Box>
            <Heading size="lg" fontFamily="'Plus Jakarta Sans', sans-serif" color={headingColor} mb={2}>{t("classes_board_page.manager")}</Heading>
            <Text color={textColor} fontFamily="'Manrope', sans-serif" dangerouslySetInnerHTML={{ __html: t("classes_board_page.manager_desc") }} />
          </Box>

          {loadingSchools ? (
            <HStack spacing={3} p={4} bg={btnOutlineHover} borderRadius="xl">
              <Spinner color={primaryColor} />
              <Text fontFamily="'Manrope', sans-serif">{t("classes_board_page.loading_schools")}</Text>
            </HStack>
          ) : schools.length === 0 ? (
            <Text color="red.500" fontFamily="'Manrope', sans-serif" dangerouslySetInnerHTML={{ __html: t("classes_board_page.no_schools") }} />
          ) : (
            <VStack align="stretch" spacing={6}>
              <Select
                placeholder={t("classes_board_page.choose")}
                value={selectedSchool}
                onChange={(e) => setSelectedSchool(e.target.value)}
                size="lg"
                bg={inputBg}
                border="1px solid"
                borderColor={inputBorder}
                borderRadius="xl"
                _focus={{ bg: panelBg, borderColor: inputFocusBorder, boxShadow: `0 0 0 1px ${inputFocusBorder}` }}
                fontFamily="'Manrope', sans-serif"
                color={headingColor}
              >
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>

              <Button
                size="lg"
                bg={primaryColor}
                color="#ffffff"
                borderRadius="full"
                _hover={{ bg: primaryHover, transform: "translateY(-1px)", boxShadow: "0px 8px 16px rgba(0, 53, 151, 0.2)" }}
                transition="all 0.2s"
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
                    title: t("classes_board_page.toast.school_selected_title"),
                    description: t("classes_board_page.toast.school_selected_desc"),
                  });
                }}
                fontFamily="'Manrope', sans-serif"
                fontWeight="bold"
              >
                {t("classes_board_page.enter_board")}
              </Button>
            </VStack>
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
          <Text>{t("classes_board_page.loading_board")}</Text>
        </HStack>
      </Flex>
    );
  }

  return (
    <Box px={{ base: 4, lg: 8 }} py={{ base: 6, lg: 8 }}>
      <VStack align="stretch" spacing={8}>
        <Box>
          <HStack justify="space-between" align="flex-start" wrap="wrap" gap={4}>
            <Box>
              <Heading
                as="h1"
                fontSize={{ base: "3xl", md: "4xl" }}
                fontWeight="extrabold"
                color={headingColor}
                fontFamily="'Plus Jakarta Sans', sans-serif"
                letterSpacing="tight"
                mb={2}
              >
                {t("classes_board_page.title")}
              </Heading>
              <Text color={textColor} fontFamily="'Manrope', sans-serif">
                {t("classes_board_page.subtitle_1")} <Text as="span" fontWeight="bold" color={primaryColor}>{t("classes_board_page.add_mode")}</Text> {t("classes_board_page.subtitle_2")} <Text as="span" fontWeight="bold" color={primaryColor}>{t("classes_board_page.move_mode")}</Text> {t("classes_board_page.subtitle_3")}
              </Text>
              <Flex 
                mt={5} 
                p={4} 
                bg="#111827" 
                borderRadius="xl" 
                align={{ base: "flex-start", md: "center" }} 
                direction={{ base: "column", md: "row" }}
                gap={4}
                border="1px solid"
                borderColor="whiteAlpha.200"
                boxShadow="0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)"
              >
                <Badge 
                  bgGradient="linear(to-r, #3b82f6, #9333ea)" 
                  color="white" 
                  px={3} 
                  py={1} 
                  borderRadius="full" 
                  textTransform="none" 
                  fontWeight="bold"
                  fontSize="xs"
                  letterSpacing="wide"
                >
                  {t("classes_board_page.soon")}
                </Badge>
                <Text color="gray.100" fontFamily="'Manrope', sans-serif" fontSize="sm" fontWeight="medium">
                  {t("classes_board_page.soon_desc")}
                </Text>
              </Flex>
            </Box>

            {/* platform_admin: muestra escuela activa y botón cambiar */}
            {isPlatformAdmin && schoolId && (
              <Flex 
                direction={{ base: "column", sm: "row" }} 
                align={{ base: "flex-start", sm: "center" }} 
                gap={3}
                w={{ base: "100%", md: "auto" }}
              >
                <Badge 
                  bg={badgeBg} 
                  color={primaryColor} 
                  borderRadius="2xl" 
                  px={4} 
                  py={1.5} 
                  textTransform="none" 
                  fontSize="sm" 
                  fontFamily="'Manrope', sans-serif"
                  whiteSpace="normal"
                  wordBreak="break-word"
                  textAlign="left"
                >
                  {t("classes_board_page.school_label")} {schoolName || schoolId}
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  borderRadius="full"
                  color={textColor}
                  borderColor={btnOutlineBorder}
                  _hover={{ bg: btnOutlineHover }}
                  fontFamily="'Manrope', sans-serif"
                  alignSelf={{ base: "flex-start", sm: "auto" }}
                  onClick={() => {
                    clearSchoolId();
                    setSchoolName("");
                    setSchoolIdState("");
                    setSelectedSchool("");
                    setSchools([]);
                    toast({
                      status: "info",
                      title: t("classes_board_page.toast.select_other_title"),
                      description: t("classes_board_page.toast.select_other_desc"),
                    });
                  }}
                >
                  {t("classes_board_page.change_school")}
                </Button>
              </Flex>
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
          <Box w="100%" overflow="hidden">
            <Flex 
              gap={6} 
              align="flex-start" 
              wrap="nowrap" 
              overflowX="auto" 
              pb={4} 
              px={2}
              css={{
                "&::-webkit-scrollbar": { height: "8px" },
                "&::-webkit-scrollbar-track": { background: "transparent" },
                "&::-webkit-scrollbar-thumb": { background: scrollbarThumb, borderRadius: "10px" },
                "&::-webkit-scrollbar-thumb:hover": { background: scrollbarThumbHover }
              }}
            >
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
                maxW="300px"
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