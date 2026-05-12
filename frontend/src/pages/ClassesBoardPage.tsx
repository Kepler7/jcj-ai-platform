import { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Divider,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Spinner,
  Text,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Radio,
  RadioGroup,
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
  assignTeacherToClass,
  createClass,
  createTeacher,
  fetchClassTeachers,
  fetchClassStudents,
  fetchMyClasses,
  fetchSchoolClasses,
  fetchSchoolTeachers,
  unassignTeacherFromClass,
  unassignStudentFromClass,
  type StudentItem,
  type TeacherItem,
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
  teachers: TeacherItem[];
  students: StudentItem[];
};

type SchoolItem = {
  id: string;
  name: string;
};

type ApiErrorLike = {
  message?: unknown;
  body?: {
    detail?: unknown;
  };
};

type RawSchool = {
  id?: unknown;
  school_id?: unknown;
  _id?: unknown;
  name?: unknown;
  school_name?: unknown;
};

function getErrorMessage(error: unknown, fallback = "Error") {
  if (typeof error === "object" && error !== null) {
    const maybeError = error as ApiErrorLike;
    if (typeof maybeError.body?.detail === "string") return maybeError.body.detail;
    if (typeof maybeError.message === "string") return maybeError.message;
  }
  return fallback;
}

// Helpers dnd
function membershipId(studentId: string, fromClassId: string) {
  return `${studentId}::${fromClassId}`;
}

function parseMembershipId(id: string) {
  const [studentId, fromClassId] = id.split("::");
  return { studentId, fromClassId };
}

function getStudentInitials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "AL";
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

function MobileSelectableStudentCard(props: {
  student: StudentItem;
  fromClassId: string;
  onSelect: (student: StudentItem, fromClassId: string) => void;
}) {
  return (
    <Box
      as="button"
      type="button"
      w="100%"
      textAlign="left"
      onClick={() => props.onSelect(props.student, props.fromClassId)}
      _focusVisible={{ outline: "3px solid", outlineColor: "blue.300", borderRadius: "xl" }}
    >
      <StudentCard student={props.student} showHint={false} interaction="select" />
    </Box>
  );
}

function NewClassCard(props: {
  canCreate: boolean;
  title: string;
  idleDescription: string;
  formDescription: string;
  inputPlaceholder: string;
  submitLabel: string;
  cancelLabel: string;
  className: string;
  isCreating: boolean;
  isFormOpen: boolean;
  onClassName: (value: string) => void;
  onOpenForm: () => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  const cardBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const borderColor = useColorModeValue("#e1e3e4", "whiteAlpha.200");
  const iconBg = useColorModeValue("#dbe1ff", "whiteAlpha.200");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryHover = useColorModeValue("#0049ca", "blue.400");
  const headingColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textColor = useColorModeValue("#737686", "whiteAlpha.500");
  const inputBg = useColorModeValue("#ffffff", "whiteAlpha.100");
  const inputBorder = useColorModeValue("rgba(195, 197, 215, 0.45)", "whiteAlpha.300");

  if (!props.canCreate) return null;

  return (
    <Flex
      minW={{ base: "100%", md: "340px" }}
      w={{ base: "100%", md: "340px" }}
      minH={{ base: "320px", md: "600px" }}
      borderRadius="2rem"
      bg={cardBg}
      border="1px solid"
      borderColor={borderColor}
      align="center"
      justify="center"
      px={8}
      py={10}
    >
      {props.isFormOpen ? (
        <VStack as="form" align="stretch" spacing={4} w="100%" onSubmit={(e) => {
          e.preventDefault();
          props.onSubmit();
        }}>
          <Box textAlign="center" mb={2}>
            <Heading size="md" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
              {props.title}
            </Heading>
            <Text mt={2} color={textColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {props.formDescription}
            </Text>
          </Box>
          <Input
            autoFocus
            placeholder={props.inputPlaceholder}
            value={props.className}
            onChange={(e) => props.onClassName(e.target.value)}
            bg={inputBg}
            borderColor={inputBorder}
            borderRadius="lg"
            fontFamily="'Manrope', sans-serif"
            isDisabled={props.isCreating}
            _focus={{ borderColor: primaryColor, boxShadow: `0 0 0 1px ${primaryColor}` }}
          />
          <Button
            type="submit"
            bg={primaryColor}
            color="#ffffff"
            borderRadius="full"
            fontFamily="'Manrope', sans-serif"
            fontWeight="bold"
            isLoading={props.isCreating}
            isDisabled={!props.className.trim()}
            _hover={{ bg: primaryHover }}
          >
            {props.submitLabel}
          </Button>
          <Button
            variant="ghost"
            borderRadius="full"
            color={textColor}
            fontFamily="'Manrope', sans-serif"
            isDisabled={props.isCreating}
            onClick={props.onCancel}
          >
            {props.cancelLabel}
          </Button>
        </VStack>
      ) : (
        <VStack spacing={4} textAlign="center">
          <Flex
            w="64px"
            h="64px"
            borderRadius="full"
            bg={iconBg}
            color={primaryColor}
            align="center"
            justify="center"
            fontSize="34px"
            lineHeight="1"
          >
            +
          </Flex>
          <Box>
            <Heading size="md" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
              {props.title}
            </Heading>
            <Text mt={2} color={textColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {props.idleDescription}
            </Text>
          </Box>
          <Button
            size="sm"
            bg={primaryColor}
            color="#ffffff"
            borderRadius="full"
            px={6}
            fontFamily="'Manrope', sans-serif"
            fontWeight="bold"
            _hover={{ bg: primaryHover }}
            onClick={props.onOpenForm}
          >
            {props.submitLabel}
          </Button>
        </VStack>
      )}
    </Flex>
  );
}

function TeachersPanel(props: {
  classes: BoardClass[];
  teachers: TeacherItem[];
  canManage: boolean;
  creatingTeacher: boolean;
  teacherActionLoading: boolean;
  teacherEmail: string;
  teacherPassword: string;
  teacherCreateClassId: string;
  selectedTeacherId: string;
  selectedTeacherClassId: string;
  onTeacherEmail: (value: string) => void;
  onTeacherPassword: (value: string) => void;
  onTeacherCreateClassId: (value: string) => void;
  onSelectedTeacherId: (value: string) => void;
  onSelectedTeacherClassId: (value: string) => void;
  onCreateTeacher: () => void;
  onAssignTeacher: () => void;
  onReassignTeacher: () => void;
  onUnassignTeacher: () => void;
}) {
  const { t } = useTranslation();
  const panelBg = useColorModeValue("#ffffff", "gray.800");
  const borderColor = useColorModeValue("rgba(195, 197, 215, 0.35)", "whiteAlpha.200");
  const headingColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textColor = useColorModeValue("#737686", "whiteAlpha.500");
  const labelColor = useColorModeValue("#434654", "gray.300");
  const inputBg = useColorModeValue("#f8f9fa", "whiteAlpha.50");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryHover = useColorModeValue("#0049ca", "blue.400");
  const softBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const badgeBg = useColorModeValue("#e8edff", "whiteAlpha.200");

  if (!props.canManage) return null;

  const selectedTeacher = props.teachers.find((teacher) => teacher.id === props.selectedTeacherId);
  const selectedTeacherClasses = props.classes.filter((klass) =>
    klass.teachers.some((teacher) => teacher.id === props.selectedTeacherId)
  );

  return (
    <Box
      bg={panelBg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="2rem"
      p={{ base: 5, md: 6 }}
      boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)"
    >
      <Flex justify="space-between" align={{ base: "flex-start", md: "center" }} gap={4} direction={{ base: "column", md: "row" }} mb={6}>
        <Box>
          <Heading size="md" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
            {t("classes_board_page.teachers.title")}
          </Heading>
          <Text mt={1} color={textColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
            {t("classes_board_page.teachers.desc")}
          </Text>
        </Box>
        <Badge bg={badgeBg} color={primaryColor} borderRadius="full" px={3} py={1} textTransform="none">
          {t("classes_board_page.teachers.count", { count: props.teachers.length })}
        </Badge>
      </Flex>

      <SimpleGrid columns={{ base: 1, xl: 2 }} spacing={6}>
        <VStack
          as="form"
          align="stretch"
          spacing={4}
          bg={softBg}
          borderRadius="xl"
          p={5}
          onSubmit={(e) => {
            e.preventDefault();
            props.onCreateTeacher();
          }}
        >
          <Box>
            <Heading size="sm" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
              {t("classes_board_page.teachers.create_title")}
            </Heading>
            <Text mt={1} color={textColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.create_desc")}
            </Text>
          </Box>

          <FormControl>
            <FormLabel color={labelColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.email_label")}
            </FormLabel>
            <Input
              type="email"
              value={props.teacherEmail}
              onChange={(e) => props.onTeacherEmail(e.target.value)}
              placeholder={t("classes_board_page.teachers.email_placeholder")}
              bg={inputBg}
              borderRadius="lg"
              isDisabled={props.creatingTeacher}
            />
          </FormControl>

          <FormControl>
            <FormLabel color={labelColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.password_label")}
            </FormLabel>
            <Input
              type="password"
              value={props.teacherPassword}
              onChange={(e) => props.onTeacherPassword(e.target.value)}
              placeholder="Teacher123!"
              bg={inputBg}
              borderRadius="lg"
              isDisabled={props.creatingTeacher}
            />
          </FormControl>

          <FormControl>
            <FormLabel color={labelColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.class_label")}
            </FormLabel>
            <Select
              value={props.teacherCreateClassId}
              onChange={(e) => props.onTeacherCreateClassId(e.target.value)}
              placeholder={t("classes_board_page.teachers.select_class")}
              bg={inputBg}
              borderRadius="lg"
              isDisabled={props.creatingTeacher || props.classes.length === 0}
            >
              {props.classes.map((klass) => (
                <option key={klass.id} value={klass.id}>
                  {klass.name}
                </option>
              ))}
            </Select>
          </FormControl>

          <Button
            type="submit"
            bg={primaryColor}
            color="#ffffff"
            borderRadius="full"
            fontFamily="'Manrope', sans-serif"
            fontWeight="bold"
            isLoading={props.creatingTeacher}
            isDisabled={!props.teacherEmail.trim() || !props.teacherPassword.trim() || !props.teacherCreateClassId}
            _hover={{ bg: primaryHover }}
          >
            {t("classes_board_page.teachers.create_and_assign")}
          </Button>
        </VStack>

        <VStack align="stretch" spacing={4} bg={softBg} borderRadius="xl" p={5}>
          <Box>
            <Heading size="sm" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
              {t("classes_board_page.teachers.assign_title")}
            </Heading>
            <Text mt={1} color={textColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.assign_desc")}
            </Text>
          </Box>

          <FormControl>
            <FormLabel color={labelColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.teacher_label")}
            </FormLabel>
            <Select
              value={props.selectedTeacherId}
              onChange={(e) => props.onSelectedTeacherId(e.target.value)}
              placeholder={t("classes_board_page.teachers.select_teacher")}
              bg={inputBg}
              borderRadius="lg"
              isDisabled={props.teacherActionLoading || props.teachers.length === 0}
            >
              {props.teachers.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.email}
                </option>
              ))}
            </Select>
          </FormControl>

          {selectedTeacher && (
            <Box bg={panelBg} borderRadius="lg" p={4}>
              <Text color={headingColor} fontWeight="bold" fontSize="sm" fontFamily="'Manrope', sans-serif" wordBreak="break-word">
                {selectedTeacher.email}
              </Text>
              <HStack mt={3} spacing={2} wrap="wrap">
                {selectedTeacherClasses.length > 0 ? (
                  selectedTeacherClasses.map((klass) => (
                    <Badge key={klass.id} bg={badgeBg} color={primaryColor} borderRadius="full" px={3} py={1} textTransform="none">
                      {klass.name}
                    </Badge>
                  ))
                ) : (
                  <Text color={textColor} fontSize="sm" fontStyle="italic">
                    {t("classes_board_page.teachers.no_assigned_classes")}
                  </Text>
                )}
              </HStack>
            </Box>
          )}

          <FormControl>
            <FormLabel color={labelColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.teachers.target_class_label")}
            </FormLabel>
            <Select
              value={props.selectedTeacherClassId}
              onChange={(e) => props.onSelectedTeacherClassId(e.target.value)}
              placeholder={t("classes_board_page.teachers.select_class")}
              bg={inputBg}
              borderRadius="lg"
              isDisabled={props.teacherActionLoading || props.classes.length === 0}
            >
              {props.classes.map((klass) => (
                <option key={klass.id} value={klass.id}>
                  {klass.name}
                </option>
              ))}
            </Select>
          </FormControl>

          <Divider borderColor={borderColor} />

          <Flex gap={3} wrap="wrap">
            <Button
              bg={primaryColor}
              color="#ffffff"
              borderRadius="full"
              fontFamily="'Manrope', sans-serif"
              fontWeight="bold"
              isLoading={props.teacherActionLoading}
              isDisabled={!props.selectedTeacherId || !props.selectedTeacherClassId}
              _hover={{ bg: primaryHover }}
              onClick={props.onAssignTeacher}
            >
              {t("classes_board_page.teachers.assign")}
            </Button>
            <Button
              variant="outline"
              borderRadius="full"
              borderColor={borderColor}
              color={headingColor}
              fontFamily="'Manrope', sans-serif"
              isDisabled={!props.selectedTeacherId || !props.selectedTeacherClassId || props.teacherActionLoading}
              onClick={props.onReassignTeacher}
            >
              {t("classes_board_page.teachers.reassign")}
            </Button>
            <Button
              variant="ghost"
              borderRadius="full"
              color="red.500"
              fontFamily="'Manrope', sans-serif"
              isDisabled={!props.selectedTeacherId || !props.selectedTeacherClassId || props.teacherActionLoading}
              onClick={props.onUnassignTeacher}
            >
              {t("classes_board_page.teachers.remove_from_class")}
            </Button>
          </Flex>
        </VStack>
      </SimpleGrid>
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
  const modalBg = useColorModeValue("#ffffff", "gray.800");
  const modalMutedColor = useColorModeValue("#737686", "whiteAlpha.600");
  const modalSectionBg = useColorModeValue("#f3f4f5", "whiteAlpha.100");
  const modalBorderColor = useColorModeValue("#e6e8ee", "whiteAlpha.200");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creatingClass, setCreatingClass] = useState(false);
  const [newClassName, setNewClassName] = useState("");
  const [showNewClassForm, setShowNewClassForm] = useState(false);

  const [mode, setMode] = useState<"add" | "move">("add");

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
  const canCreateClass = me?.role === "platform_admin" || me?.role === "school_admin";
  const canManageTeachers = me?.role === "platform_admin" || me?.role === "school_admin";
  const [schoolName, setSchoolName] = useState<string>(getSchoolName());
  const [teachers, setTeachers] = useState<TeacherItem[]>([]);
  const [creatingTeacher, setCreatingTeacher] = useState(false);
  const [teacherActionLoading, setTeacherActionLoading] = useState(false);
  const [teacherEmail, setTeacherEmail] = useState("");
  const [teacherPassword, setTeacherPassword] = useState("");
  const [teacherCreateClassId, setTeacherCreateClassId] = useState("");
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [selectedTeacherClassId, setSelectedTeacherClassId] = useState("");
  const [mobileSelection, setMobileSelection] = useState<{
    student: StudentItem;
    fromClassId: string;
  } | null>(null);
  const [mobileMode, setMobileMode] = useState<"add" | "move">("add");
  const [mobileTargetClassId, setMobileTargetClassId] = useState("");
  const [mobileUpdating, setMobileUpdating] = useState(false);

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
        const data = await api<unknown>("/v1/schools", { auth: true });

        // Intento tolerante: acepta {items:[...]} o array directo
        const dataWithItems = data as { items?: unknown };
        const list = Array.isArray(data)
          ? data
          : Array.isArray(dataWithItems?.items)
            ? dataWithItems.items
            : [];

        // Normaliza campos si vienen diferentes
        const normalized = list
          .map((raw) => {
            const s = raw as RawSchool;
            return {
              id: String(s.id ?? s.school_id ?? s._id ?? ""),
              name: String(s.name ?? s.school_name ?? t("classes_board_page.school_fallback")),
            };
          })
          .filter((s) => s.id);

        normalized.sort((a, b) => a.name.localeCompare(b.name, "es"));

        setSchools(normalized);
      } catch (e: unknown) {
        setSchools([]);
        toast({
          status: "error",
          title: t("classes_board_page.toast.error_loading_schools_title"),
          description: getErrorMessage(e, t("classes_board_page.toast.error_loading_schools_desc")),
        });
      } finally {
        setLoadingSchools(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlatformAdmin, schoolId]);

  async function loadBoard(sid: string) {
    const cls = me?.role === "teacher" ? await fetchMyClasses() : await fetchSchoolClasses(sid);

    const results = await Promise.all(
      cls.map(async (c) => {
        const [students, classTeachers] = await Promise.all([
          fetchClassStudents(c.id),
          canManageTeachers ? fetchClassTeachers(c.id) : Promise.resolve([]),
        ]);
        return { id: c.id, name: c.name, teachers: classTeachers, students };
      })
    );

    results.sort((a, b) => a.name.localeCompare(b.name, "es"));
    setClasses(results);

    if (canManageTeachers) {
      const schoolTeachers = await fetchSchoolTeachers(sid);
      setTeachers(schoolTeachers.sort((a, b) => a.email.localeCompare(b.email, "es")));
    } else {
      setTeachers([]);
    }
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
      } catch (e: unknown) {
        toast({
          status: "error",
          title: t("classes_board_page.toast.error_loading_board_title"),
          description: getErrorMessage(e),
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
    } catch (e: unknown) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.error_refreshing_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setRefreshing(false);
    }
  }

  async function handleCreateClass() {
    const name = newClassName.trim();

    if (!schoolId) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.missing_school_id_title"),
        description: t("classes_board_page.toast.missing_refresh_id_desc"),
      });
      return;
    }

    if (!name) return;

    try {
      setCreatingClass(true);
      const created = await createClass(schoolId, name);

      setClasses((prev) => {
        const next = [
          ...prev,
          {
            id: created.id,
            name: created.name,
            teachers: [],
            students: [],
          },
        ];
        return next.sort((a, b) => a.name.localeCompare(b.name, "es"));
      });
      setNewClassName("");
      setShowNewClassForm(false);

      toast({
        status: "success",
        title: t("classes_board_page.toast.class_created_title"),
        description: t("classes_board_page.toast.class_created_desc"),
      });
    } catch (e: unknown) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.class_create_error_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setCreatingClass(false);
    }
  }

  function updateClassTeachers(classId: string, updater: (current: TeacherItem[]) => TeacherItem[]) {
    setClasses((prev) =>
      prev.map((klass) =>
        klass.id === classId
          ? { ...klass, teachers: updater(klass.teachers) }
          : klass
      )
    );
  }

  function getTeacherAssignedClasses(teacherId: string) {
    return classes.filter((klass) =>
      klass.teachers.some((teacher) => teacher.id === teacherId)
    );
  }

  async function handleCreateTeacher() {
    const email = teacherEmail.trim();
    const password = teacherPassword.trim();

    if (!schoolId || !email || !password || !teacherCreateClassId) return;

    try {
      setCreatingTeacher(true);
      const teacher = await createTeacher({ schoolId, email, password });
      await assignTeacherToClass(teacherCreateClassId, teacher.id);

      setTeachers((prev) => {
        const exists = prev.some((item) => item.id === teacher.id);
        const next = exists ? prev : [...prev, teacher];
        return next.sort((a, b) => a.email.localeCompare(b.email, "es"));
      });
      updateClassTeachers(teacherCreateClassId, (current) =>
        current.some((item) => item.id === teacher.id) ? current : [...current, teacher]
      );
      setSelectedTeacherId(teacher.id);
      setSelectedTeacherClassId(teacherCreateClassId);
      setTeacherEmail("");
      setTeacherPassword("");

      toast({
        status: "success",
        title: t("classes_board_page.toast.teacher_created_title"),
        description: t("classes_board_page.toast.teacher_created_desc"),
      });
    } catch (e: unknown) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.teacher_create_error_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setCreatingTeacher(false);
    }
  }

  async function handleAssignTeacher() {
    const teacher = teachers.find((item) => item.id === selectedTeacherId);
    if (!teacher || !selectedTeacherClassId) return;

    try {
      setTeacherActionLoading(true);
      await assignTeacherToClass(selectedTeacherClassId, teacher.id);
      updateClassTeachers(selectedTeacherClassId, (current) =>
        current.some((item) => item.id === teacher.id) ? current : [...current, teacher]
      );
      toast({
        status: "success",
        title: t("classes_board_page.toast.teacher_assigned_title"),
        description: t("classes_board_page.toast.teacher_assigned_desc"),
      });
    } catch (e: unknown) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.teacher_assign_error_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setTeacherActionLoading(false);
    }
  }

  async function handleReassignTeacher() {
    const teacher = teachers.find((item) => item.id === selectedTeacherId);
    if (!teacher || !selectedTeacherClassId) return;

    const assignedClasses = getTeacherAssignedClasses(teacher.id);

    try {
      setTeacherActionLoading(true);
      await Promise.all(
        assignedClasses
          .filter((klass) => klass.id !== selectedTeacherClassId)
          .map((klass) => unassignTeacherFromClass(klass.id, teacher.id))
      );
      await assignTeacherToClass(selectedTeacherClassId, teacher.id);

      setClasses((prev) =>
        prev.map((klass) => {
          const withoutTeacher = klass.teachers.filter((item) => item.id !== teacher.id);
          if (klass.id === selectedTeacherClassId) {
            return { ...klass, teachers: [...withoutTeacher, teacher] };
          }
          return { ...klass, teachers: withoutTeacher };
        })
      );

      toast({
        status: "success",
        title: t("classes_board_page.toast.teacher_reassigned_title"),
        description: t("classes_board_page.toast.teacher_reassigned_desc"),
      });
    } catch (e: unknown) {
      await refresh();
      toast({
        status: "error",
        title: t("classes_board_page.toast.teacher_reassign_error_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setTeacherActionLoading(false);
    }
  }

  async function handleUnassignTeacher() {
    const teacher = teachers.find((item) => item.id === selectedTeacherId);
    if (!teacher || !selectedTeacherClassId) return;

    try {
      setTeacherActionLoading(true);
      await unassignTeacherFromClass(selectedTeacherClassId, teacher.id);
      updateClassTeachers(selectedTeacherClassId, (current) =>
        current.filter((item) => item.id !== teacher.id)
      );
      toast({
        status: "success",
        title: t("classes_board_page.toast.teacher_removed_title"),
        description: t("classes_board_page.toast.teacher_removed_desc"),
      });
    } catch (e: unknown) {
      toast({
        status: "error",
        title: t("classes_board_page.toast.teacher_remove_error_title"),
        description: getErrorMessage(e),
      });
    } finally {
      setTeacherActionLoading(false);
    }
  }

  useEffect(() => {
    if (!classes.length) return;

    setTeacherCreateClassId((current) =>
      current && classes.some((klass) => klass.id === current) ? current : classes[0].id
    );
    setSelectedTeacherClassId((current) =>
      current && classes.some((klass) => klass.id === current) ? current : classes[0].id
    );
  }, [classes]);

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

  async function updateStudentClass(params: {
    studentId: string;
    fromClassId: string;
    toClassId: string;
    actionMode: "add" | "move";
  }) {
    const { studentId, fromClassId, toClassId, actionMode } = params;
    if (fromClassId === toClassId) return;

    const targetHas = classes
      .find((c) => c.id === toClassId)
      ?.students.some((s) => s.id === studentId);

    if (actionMode === "add" && targetHas) {
      toast({
        status: "info",
        title: t("classes_board_page.toast.enrolled_title"),
        description: t("classes_board_page.toast.enrolled_desc"),
      });
      return;
    }

    optimisticMoveOrAdd({ studentId, fromClassId, toClassId, mode: actionMode });

    try {
      if (actionMode === "move") {
        await unassignStudentFromClass(fromClassId, studentId);
        await assignStudentToClass(toClassId, studentId);
      } else {
        await assignStudentToClass(toClassId, studentId);
      }

      toast({
        status: "success",
        title: actionMode === "move" ? t("classes_board_page.toast.moved_title") : t("classes_board_page.toast.enrolled_success_title"),
        description:
          actionMode === "move"
            ? t("classes_board_page.toast.moved_desc")
            : t("classes_board_page.toast.enrolled_success_desc"),
      });
    } catch (e: unknown) {
      rollback();
      toast({
        status: "error",
        title: t("classes_board_page.toast.update_error_title"),
        description: getErrorMessage(e),
      });
    }
  }

  async function onDragEnd(ev: DragEndEvent) {
    setActiveMembership(null);

    const overId = ev.over?.id ? String(ev.over.id) : null;
    const activeId = String(ev.active.id);

    if (!overId) return;
    if (!activeId.includes("::")) return;

    const { studentId, fromClassId } = parseMembershipId(activeId);
    await updateStudentClass({ studentId, fromClassId, toClassId: overId, actionMode: mode });
  }

  function openMobileStudentModal(student: StudentItem, fromClassId: string) {
    setMobileSelection({ student, fromClassId });
    setMobileMode(mode);
    setMobileTargetClassId("");
  }

  function closeMobileStudentModal() {
    if (mobileUpdating) return;
    setMobileSelection(null);
    setMobileTargetClassId("");
  }

  async function submitMobileStudentUpdate() {
    if (!mobileSelection || !mobileTargetClassId) return;

    try {
      setMobileUpdating(true);
      await updateStudentClass({
        studentId: mobileSelection.student.id,
        fromClassId: mobileSelection.fromClassId,
        toClassId: mobileTargetClassId,
        actionMode: mobileMode,
      });
      setMobileSelection(null);
      setMobileTargetClassId("");
    } finally {
      setMobileUpdating(false);
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

        <TeachersPanel
          classes={classes}
          teachers={teachers}
          canManage={canManageTeachers && Boolean(schoolId)}
          creatingTeacher={creatingTeacher}
          teacherActionLoading={teacherActionLoading}
          teacherEmail={teacherEmail}
          teacherPassword={teacherPassword}
          teacherCreateClassId={teacherCreateClassId}
          selectedTeacherId={selectedTeacherId}
          selectedTeacherClassId={selectedTeacherClassId}
          onTeacherEmail={setTeacherEmail}
          onTeacherPassword={setTeacherPassword}
          onTeacherCreateClassId={setTeacherCreateClassId}
          onSelectedTeacherId={setSelectedTeacherId}
          onSelectedTeacherClassId={setSelectedTeacherClassId}
          onCreateTeacher={handleCreateTeacher}
          onAssignTeacher={handleAssignTeacher}
          onReassignTeacher={handleReassignTeacher}
          onUnassignTeacher={handleUnassignTeacher}
        />

        <BoardToolbar
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
          <Box w="100%" overflow="visible" position="relative">
            <Flex
              gap={6}
              align="flex-start"
              direction={{ base: "column", md: "row" }}
              wrap={{ base: "nowrap", md: "nowrap" }}
              overflowX={{ base: "visible", md: "auto" }}
              pb={4}
              px={2}
              css={{
                "&::-webkit-scrollbar": { height: "8px" },
                "&::-webkit-scrollbar-track": { background: "transparent" },
                "&::-webkit-scrollbar-thumb": { background: scrollbarThumb, borderRadius: "10px" },
                "&::-webkit-scrollbar-thumb:hover": { background: scrollbarThumbHover }
              }}
            >
              {classes.map((c) => (
                <ClassColumn
                  key={c.id}
                  classId={c.id}
                  name={c.name}
                  count={c.students.length}
                  teachers={c.teachers.map((teacher) => teacher.email)}
                >
                  {c.students.map((s) => (
                    <Box key={membershipId(s.id, c.id)}>
                      <Box display={{ base: "block", md: "none" }}>
                        <MobileSelectableStudentCard
                          student={s}
                          fromClassId={c.id}
                          onSelect={openMobileStudentModal}
                        />
                      </Box>
                      <Box display={{ base: "none", md: "block" }}>
                        <DraggableStudentCard
                          student={s}
                          fromClassId={c.id}
                          showHint={false}
                        />
                      </Box>
                    </Box>
                  ))}
                </ClassColumn>
              ))}
              <NewClassCard
                canCreate={canCreateClass && Boolean(schoolId)}
                title={t("classes_board_page.new_class.title")}
                idleDescription={t("classes_board_page.new_class.idle_desc")}
                formDescription={t("classes_board_page.new_class.form_desc")}
                inputPlaceholder={t("classes_board_page.new_class.placeholder")}
                submitLabel={t("classes_board_page.new_class.submit")}
                cancelLabel={t("classes_board_page.new_class.cancel")}
                className={newClassName}
                isCreating={creatingClass}
                isFormOpen={showNewClassForm}
                onClassName={setNewClassName}
                onOpenForm={() => setShowNewClassForm(true)}
                onCancel={() => {
                  setShowNewClassForm(false);
                  setNewClassName("");
                }}
                onSubmit={handleCreateClass}
              />
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

        <Modal isOpen={Boolean(mobileSelection)} onClose={closeMobileStudentModal} isCentered>
          <ModalOverlay />
          <ModalContent bg={modalBg} borderRadius="2xl" mx={4} overflow="hidden" maxW="580px">
            <ModalHeader px={7} pt={7} pb={5} borderBottom="1px solid" borderColor={modalBorderColor}>
              <Heading size="md" color={headingColor} fontFamily="'Plus Jakarta Sans', sans-serif">
                {t("classes_board_page.mobile_action.title")}
              </Heading>
              <Text mt={1} color={modalMutedColor} fontSize="sm" fontFamily="'Manrope', sans-serif" fontWeight="normal">
                {t("classes_board_page.mobile_action.subtitle")}
              </Text>
            </ModalHeader>
            <ModalCloseButton top={5} right={5} color={modalMutedColor} isDisabled={mobileUpdating} />
            <ModalBody px={7} py={7}>
              <VStack align="stretch" spacing={6}>
                <Box>
                  <Text
                    color={modalMutedColor}
                    fontSize="xs"
                    fontWeight="extrabold"
                    letterSpacing="wide"
                    textTransform="uppercase"
                    fontFamily="'Manrope', sans-serif"
                    mb={3}
                  >
                    {t("classes_board_page.mobile_action.student_label")}
                  </Text>
                  <Flex align="center" gap={4} bg={modalSectionBg} borderRadius="xl" px={4} py={4}>
                    <Flex
                      w="54px"
                      h="54px"
                      flex="0 0 auto"
                      borderRadius="full"
                      bg={primaryColor}
                      color="#ffffff"
                      align="center"
                      justify="center"
                      fontWeight="extrabold"
                      fontFamily="'Manrope', sans-serif"
                    >
                      {getStudentInitials(mobileSelection?.student.full_name ?? "")}
                    </Flex>
                    <Box minW={0}>
                      <Text color={headingColor} fontWeight="extrabold" fontSize="lg" fontFamily="'Manrope', sans-serif" noOfLines={1}>
                        {mobileSelection?.student.full_name}
                      </Text>
                      <Text color={modalMutedColor} fontSize="sm" fontFamily="'Manrope', sans-serif">
                        ID: #{(mobileSelection?.student.id ?? "").slice(0, 4)}
                      </Text>
                    </Box>
                  </Flex>
                </Box>

                <FormControl>
                  <FormLabel
                    color={modalMutedColor}
                    fontSize="xs"
                    fontWeight="extrabold"
                    letterSpacing="wide"
                    textTransform="uppercase"
                    fontFamily="'Manrope', sans-serif"
                  >
                    {t("classes_board_page.mobile_action.mode_label")}
                  </FormLabel>
                  <RadioGroup
                    value={mobileMode}
                    onChange={(value) => setMobileMode(value as "add" | "move")}
                  >
                    <SimpleGrid columns={2} spacing={4}>
                      <Radio
                        value="add"
                        colorScheme="blue"
                        isDisabled={mobileUpdating}
                        border="2px solid"
                        borderColor={mobileMode === "add" ? primaryColor : modalBorderColor}
                        borderRadius="lg"
                        px={4}
                        py={4}
                        fontWeight="extrabold"
                        fontFamily="'Manrope', sans-serif"
                        bg={mobileMode === "add" ? badgeBg : "transparent"}
                      >
                        {t("classes_board_page.add_mode")}
                      </Radio>
                      <Radio
                        value="move"
                        colorScheme="blue"
                        isDisabled={mobileUpdating}
                        border="2px solid"
                        borderColor={mobileMode === "move" ? primaryColor : modalBorderColor}
                        borderRadius="lg"
                        px={4}
                        py={4}
                        fontWeight="extrabold"
                        fontFamily="'Manrope', sans-serif"
                        bg={mobileMode === "move" ? badgeBg : "transparent"}
                      >
                        {t("classes_board_page.move_mode")}
                      </Radio>
                    </SimpleGrid>
                  </RadioGroup>
                </FormControl>

                <FormControl>
                  <FormLabel
                    color={modalMutedColor}
                    fontSize="xs"
                    fontWeight="extrabold"
                    letterSpacing="wide"
                    textTransform="uppercase"
                    fontFamily="'Manrope', sans-serif"
                  >
                    {t("classes_board_page.mobile_action.target_label")}
                  </FormLabel>
                  <Select
                    value={mobileTargetClassId}
                    onChange={(event) => setMobileTargetClassId(event.target.value)}
                    placeholder={t("classes_board_page.mobile_action.target_placeholder")}
                    bg={modalSectionBg}
                    h="64px"
                    fontSize="md"
                    borderRadius="lg"
                    borderColor={modalBorderColor}
                    isDisabled={mobileUpdating}
                  >
                    {classes
                      .filter((klass) => klass.id !== mobileSelection?.fromClassId)
                      .map((klass) => (
                        <option key={klass.id} value={klass.id}>
                          {klass.name}
                        </option>
                      ))}
                  </Select>
                </FormControl>
              </VStack>
            </ModalBody>
            <ModalFooter gap={3} px={7} py={6} bg={modalSectionBg} borderTop="1px solid" borderColor={modalBorderColor}>
              <Button
                variant="ghost"
                borderRadius="full"
                color={primaryColor}
                fontWeight="extrabold"
                onClick={closeMobileStudentModal}
                isDisabled={mobileUpdating}
              >
                {t("classes_board_page.mobile_action.cancel")}
              </Button>
              <Button
                bg={primaryColor}
                color="#ffffff"
                borderRadius="full"
                px={9}
                h="56px"
                fontWeight="extrabold"
                _hover={{ bg: primaryHover }}
                isLoading={mobileUpdating}
                isDisabled={!mobileTargetClassId}
                onClick={submitMobileStudentUpdate}
              >
                {t("classes_board_page.mobile_action.accept")}
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Box>
  );
}
