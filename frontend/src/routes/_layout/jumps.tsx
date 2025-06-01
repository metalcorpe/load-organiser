import {
  Avatar,
  Badge,
  Box,
  Button,
  Container,
  Flex,
  HStack,
  Heading,
  IconButton,
  Input,
  Separator,
  SimpleGrid,
  Table,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { FiEdit, FiPlus, FiSearch, FiTrash2, FiUsers } from "react-icons/fi"

import { type ApiError, type JumpPublic, JumpsService } from "../../client"
import {
  DialogActionTrigger,
  DialogBody,
  DialogContent,
  // DialogTrigger,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "../../components/ui/dialog"
import { Field } from "../../components/ui/field"
import { InputGroup } from "../../components/ui/input-group"
import useCustomToast from "../../hooks/useCustomToast"

export const Route = createFileRoute("/_layout/jumps")({
  component: Jumps,
})

function Jumps() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { open: isOpen, onOpen, onClose } = useDisclosure()
  const [selectedJump, setSelectedJump] = useState<JumpPublic | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  // const [statusFilter, setStatusFilter] = useState("all");

  // Fetch jumps data
  const {
    data: jumpsResponse,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["jumps"],
    queryFn: () => JumpsService.readJumps({}),
  })

  const jumps = jumpsResponse?.data || []

  const filteredJumps = jumps.filter((jump) => {
    const matchesSearch =
      jump.jumper_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      jump.jump_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      jump.instructor?.name?.toLowerCase().includes(searchTerm.toLowerCase())

    // Remove status filtering since status property doesn't exist
    return matchesSearch
  })

  // Calculate statistics
  // Calculate statistics
  const totalJumps = jumps.length
  const todayJumps = jumps.filter((jump) => {
    const today = new Date().toISOString().split("T")[0]
    return jump.created_at?.includes(today)
  }).length
  const completedJumps = 0 // Remove status-based filtering since status doesn't exist
  const pendingJumps = 0 // Remove status-based filtering since status doesn't exist
  const handleEditJump = (jump: JumpPublic) => {
    setSelectedJump(jump)
    onOpen()
  }

  const handleDeleteJump = async (jumpId: string) => {
    try {
      await JumpsService.deleteJump({ id: jumpId })
      queryClient.invalidateQueries({ queryKey: ["jumps"] })
      showSuccessToast("Jump deleted successfully")
    } catch (error) {
      const apiError = error as ApiError
      const errDetail =
        apiError.body &&
        typeof apiError.body === "object" &&
        apiError.body !== null &&
        "detail" in apiError.body
          ? (apiError.body as { detail: string }).detail
          : "Something went wrong"
      showErrorToast(errDetail)
    }
  }

  // const getStatusColor = (status: string) => {
  //   switch (status) {
  //     case "scheduled":
  //       return "blue";
  //     case "in_progress":
  //       return "yellow";
  //     case "completed":
  //       return "green";
  //     case "cancelled":
  //       return "red";
  //     default:
  //       return "gray";
  //   }
  // };

  const getJumpTypeColor = (jumpType: string) => {
    switch (jumpType) {
      case "tandem":
        return "purple"
      case "aff":
        return "orange"
      case "fun_jump":
        return "teal"
      case "coach_jump":
        return "cyan"
      default:
        return "gray"
    }
  }

  if (isLoading) {
    return (
      <Container maxW="full">
        <Box p={8} textAlign="center">
          <Text>Loading jumps...</Text>
        </Box>
      </Container>
    )
  }

  if (isError) {
    return (
      <Container maxW="full">
        <Box p={8} textAlign="center">
          <Text color="red.500">Error loading jumps data</Text>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg">Jump Management</Heading>
            <Text color="gray.600">Manage and track all jump activities</Text>
          </Box>
          <Button colorScheme="blue" size="lg" onClick={onOpen}>
            <FiPlus style={{ marginRight: "8px" }} />
            Schedule Jump
          </Button>
        </Flex>

        <Separator />

        {/* Statistics Cards */}
        <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiUsers color="blue" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Total Jumps
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {totalJumps}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <VStack align="start" gap={0}>
              <Text fontSize="sm" color="gray.600">
                Today's Jumps
              </Text>
              <Text fontSize="2xl" fontWeight="bold">
                {todayJumps}
              </Text>
            </VStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <VStack align="start" gap={0}>
              <Text fontSize="sm" color="gray.600">
                Completed
              </Text>
              <Text fontSize="2xl" fontWeight="bold" color="green.500">
                {completedJumps}
              </Text>
            </VStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <VStack align="start" gap={0}>
              <Text fontSize="sm" color="gray.600">
                Pending
              </Text>
              <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                {pendingJumps}
              </Text>
            </VStack>
          </Box>
        </SimpleGrid>

        {/* Filters */}
        <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
          <HStack gap={4}>
            <Field label="Search">
              <InputGroup startElement={<FiSearch color="gray" />} maxW="300px">
                <Input
                  placeholder="Search jumps..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </InputGroup>
            </Field>
          </HStack>
        </Box>

        {/* Jumps Table */}
        <Box bg="white" borderRadius="lg" borderWidth="1px" overflow="hidden">
          <Box p={4} borderBottom="1px" borderColor="gray.200">
            <Heading size="md">Jump Schedule</Heading>
          </Box>

          {isLoading ? (
            <Box p={8} textAlign="center">
              <Text>Loading jumps...</Text>
            </Box>
          ) : filteredJumps.length === 0 ? (
            <Box p={8} textAlign="center">
              <Text color="gray.500" mb={4}>
                No jumps scheduled yet
              </Text>
              <Button colorScheme="blue" onClick={onOpen}>
                <FiPlus style={{ marginRight: "8px" }} />
                Schedule First Jump
              </Button>
            </Box>
          ) : (
            <Table.Root size={{ base: "sm", md: "md" }}>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>Jumper</Table.ColumnHeader>
                  <Table.ColumnHeader>Type</Table.ColumnHeader>
                  <Table.ColumnHeader>Instructor</Table.ColumnHeader>
                  <Table.ColumnHeader>Load</Table.ColumnHeader>
                  <Table.ColumnHeader>Time</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {filteredJumps.map((jump) => (
                  <Table.Row key={jump.id}>
                    <Table.Cell>
                      <VStack align="start" gap={1}>
                        <Text fontWeight="medium">{jump.jumper_name}</Text>
                        {jump.customer_email && (
                          <Text fontSize="sm" color="gray.500">
                            {jump.customer_email}
                          </Text>
                        )}
                      </VStack>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge
                        colorScheme={getJumpTypeColor(jump.jump_type || "")}
                        variant="subtle"
                      >
                        {jump.jump_type?.toUpperCase()}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <HStack>
                        <Avatar.Root size="sm">
                          <Avatar.Fallback>
                            {(jump.instructor?.name || "U")
                              .charAt(0)
                              .toUpperCase()}
                          </Avatar.Fallback>
                        </Avatar.Root>
                        <Text>{jump.instructor?.name || "Unassigned"}</Text>
                      </HStack>
                    </Table.Cell>
                    <Table.Cell>
                      <Text>Load #{jump.load_id}</Text>
                    </Table.Cell>
                    <Table.Cell>
                      <VStack align="start" gap={1}>
                        <Text fontSize="sm">
                          {jump.created_at
                            ? new Date(jump.created_at).toLocaleDateString()
                            : "TBD"}
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          {jump.created_at
                            ? new Date(jump.created_at).toLocaleTimeString()
                            : ""}
                        </Text>
                      </VStack>
                    </Table.Cell>
                    <Table.Cell>
                      <Table.Cell>
                        <Badge colorScheme="gray" variant="subtle">
                          Scheduled
                        </Badge>
                      </Table.Cell>
                      <HStack gap={2}>
                        <IconButton
                          aria-label="Edit jump"
                          size="sm"
                          variant="ghost"
                          colorScheme="blue"
                          onClick={() => handleEditJump(jump)}
                        >
                          <FiEdit />
                        </IconButton>
                        <IconButton
                          aria-label="Delete jump"
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => jump.id && handleDeleteJump(jump.id)}
                        >
                          <FiTrash2 />
                        </IconButton>
                      </HStack>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Root>
          )}
        </Box>

        {/* Quick Actions */}
        <Box p={6} bg="gray.50" borderRadius="lg">
          <Heading size="sm" mb={3}>
            Quick Actions
          </Heading>
          <HStack gap={3} flexWrap="wrap">
            <Button size="sm" colorScheme="blue">
              Schedule Jump
            </Button>
            <Button size="sm" variant="outline">
              View Today's Manifest
            </Button>
            <Button size="sm" variant="outline">
              Jump Reports
            </Button>
            <Button size="sm" variant="outline">
              Instructor Assignments
            </Button>
          </HStack>
        </Box>
      </VStack>

      {/* Jump Form Dialog */}
      <DialogRoot open={isOpen} onOpenChange={({ open }) => !open && onClose()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedJump ? "Edit Jump" : "Schedule New Jump"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text color="gray.500" mb={4}>
              Jump scheduling form will be implemented here with fields for:
            </Text>
            <VStack align="start" gap={2} pl={4}>
              <Text fontSize="sm">
                • Jumper information and contact details
              </Text>
              <Text fontSize="sm">
                • Jump type selection (Tandem, AFF, Fun Jump, etc.)
              </Text>
              <Text fontSize="sm">• Instructor assignment</Text>
              <Text fontSize="sm">• Load assignment and slot number</Text>
              <Text fontSize="sm">• Scheduled time and date</Text>
              <Text fontSize="sm">• Equipment requirements</Text>
              <Text fontSize="sm">• Special notes and requirements</Text>
            </VStack>
          </DialogBody>
          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button variant="ghost">Cancel</Button>
            </DialogActionTrigger>
            <Button colorScheme="blue">
              {selectedJump ? "Update Jump" : "Schedule Jump"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Container>
  )
}
