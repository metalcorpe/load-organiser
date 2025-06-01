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
  Separator,
  SimpleGrid,
  Table,
  Tag,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  FiAward,
  FiEdit,
  FiPlus,
  FiTrash2,
  FiUser,
  FiUsers,
} from "react-icons/fi"

import { InstructorsService } from "../../client"
import type { InstructorPublic } from "../../client"
import InstructorForm from "../../components/Forms/InstructorForm"
import {
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "../../components/ui/dialog"
import useCustomToast from "../../hooks/useCustomToast"

export const Route = createFileRoute("/_layout/instructors")({
  component: InstructorsPage,
})

function InstructorsPage() {
  const queryClient = useQueryClient()
  const [selectedInstructor, setSelectedInstructor] =
    useState<InstructorPublic | null>(null)
  const [isCreateMode, setIsCreateMode] = useState(false)
  const { open: isOpen, onOpen, onClose } = useDisclosure()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: instructorsResponse, isLoading } = useQuery({
    queryKey: ["instructors"],
    queryFn: () => InstructorsService.readInstructors({}),
  })

  const deleteInstructorMutation = useMutation({
    mutationFn: (instructorId: string) =>
      InstructorsService.deleteInstructor({ id: instructorId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instructors"] })
      showSuccessToast("Instructor deleted successfully!")
    },
    onError: (error: any) => {
      showErrorToast("Failed to delete instructor. Please try again.")
      console.error("Error deleting instructor:", error)
    },
  })

  const toggleInstructorStatusMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      InstructorsService.updateInstructor({
        id,
        requestBody: { is_active: !isActive },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instructors"] })
    },
  })

  const instructors = instructorsResponse?.data || []
  const activeInstructors = instructors.filter(
    (inst: InstructorPublic) => inst.is_active,
  )
  const tandemCertified = instructors.filter(
    (inst: InstructorPublic) => inst.tandem_certified && inst.is_active,
  )
  const affCertified = instructors.filter(
    (inst: InstructorPublic) => inst.aff_certified && inst.is_active,
  )

  const handleDeleteInstructor = (instructorId: string) => {
    if (window.confirm("Are you sure you want to delete this instructor?")) {
      deleteInstructorMutation.mutate(instructorId)
    }
  }

  const handleToggleStatus = (instructor: InstructorPublic) => {
    toggleInstructorStatusMutation.mutate({
      id: instructor.id,
      isActive: instructor.is_active || false,
    })
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg">Instructor Management</Heading>
            <Text color="gray.600">Manage certified skydiving instructors</Text>
          </Box>
          <Button
            colorScheme="blue"
            size="lg"
            onClick={() => {
              setSelectedInstructor(null)
              setIsCreateMode(true)
              onOpen()
            }}
          >
            <FiPlus style={{ marginRight: "8px" }} />
            Add New Instructor
          </Button>
        </Flex>

        <Separator />

        {/* Stats Summary */}
        <SimpleGrid columns={{ base: 1, md: 4 }} gap={4}>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiUsers color="blue" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Total Instructors
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {instructors.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiUser color="green" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Active Instructors
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {activeInstructors.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiAward color="purple" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Tandem Certified
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {tandemCertified.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiAward color="orange" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  AFF Certified
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {affCertified.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
        </SimpleGrid>

        {/* Instructors Table */}
        <Box bg="white" borderRadius="lg" borderWidth="1px" overflow="hidden">
          <Box p={4} borderBottom="1px" borderColor="gray.200">
            <Heading size="md">Instructor Directory</Heading>
          </Box>

          {isLoading ? (
            <Box p={8} textAlign="center">
              <Text>Loading instructors...</Text>
            </Box>
          ) : instructors.length === 0 ? (
            <Box p={8} textAlign="center">
              <Text color="gray.500" mb={4}>
                No instructors registered yet
              </Text>
              <Button colorScheme="blue">
                <FiPlus style={{ marginRight: "8px" }} />
                Add First Instructor
              </Button>
            </Box>
          ) : (
            <Table.Root>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>Instructor</Table.ColumnHeader>
                  <Table.ColumnHeader>Email</Table.ColumnHeader>
                  <Table.ColumnHeader>Certifications</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {instructors.map((instructor: InstructorPublic) => (
                  <Table.Row key={instructor.id}>
                    <Table.Cell>
                      <HStack>
                        <Avatar.Root size="sm">
                          <Avatar.Fallback bg="blue.500" color="white">
                            {getInitials(instructor.name)}
                          </Avatar.Fallback>
                        </Avatar.Root>
                        <Text fontWeight="semibold">{instructor.name}</Text>
                      </HStack>
                    </Table.Cell>
                    <Table.Cell>{instructor.email}</Table.Cell>
                    <Table.Cell>
                      <HStack gap={2}>
                        {instructor.tandem_certified && (
                          <Tag.Root
                            size="sm"
                            colorScheme="purple"
                            variant="subtle"
                          >
                            <Tag.Label>Tandem</Tag.Label>
                          </Tag.Root>
                        )}
                        {instructor.aff_certified && (
                          <Tag.Root
                            size="sm"
                            colorScheme="orange"
                            variant="subtle"
                          >
                            <Tag.Label>AFF</Tag.Label>
                          </Tag.Root>
                        )}
                        {!instructor.tandem_certified &&
                          !instructor.aff_certified && (
                            <Text fontSize="sm" color="gray.500">
                              No certifications
                            </Text>
                          )}
                      </HStack>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge
                        colorScheme={instructor.is_active ? "green" : "red"}
                        variant="subtle"
                      >
                        {instructor.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <HStack gap={2}>
                        <IconButton
                          aria-label="Edit instructor"
                          size="sm"
                          variant="ghost"
                          colorScheme="blue"
                          onClick={() => {
                            setSelectedInstructor(instructor)
                            setIsCreateMode(false)
                            onOpen()
                          }}
                        >
                          <FiEdit />
                        </IconButton>
                        <Button
                          size="sm"
                          variant="ghost"
                          colorScheme={instructor.is_active ? "red" : "green"}
                          onClick={() => handleToggleStatus(instructor)}
                        >
                          {instructor.is_active ? "Deactivate" : "Activate"}
                        </Button>
                        <IconButton
                          aria-label="Delete instructor"
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => handleDeleteInstructor(instructor.id)}
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
            <Button
              size="sm"
              colorScheme="blue"
              onClick={() => {
                setSelectedInstructor(null)
                setIsCreateMode(true)
                onOpen()
              }}
            >
              Add Instructor
            </Button>
            <Button size="sm" variant="outline">
              Import from CSV
            </Button>
            <Button size="sm" variant="outline">
              Export Directory
            </Button>
            <Button size="sm" variant="outline">
              Certification Report
            </Button>
            <Button size="sm" variant="outline">
              Schedule View
            </Button>
          </HStack>
        </Box>
      </VStack>

      {/* Instructor Form Modal */}
      <DialogRoot open={isOpen} onOpenChange={onClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isCreateMode ? "Add New Instructor" : "Edit Instructor"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <InstructorForm
              type={isCreateMode ? "create" : "update"}
              instructor={selectedInstructor || undefined}
              onSuccess={() => {
                queryClient.invalidateQueries({ queryKey: ["instructors"] })
                showSuccessToast(
                  isCreateMode
                    ? "Instructor created successfully!"
                    : "Instructor updated successfully!",
                )
                onClose()
              }}
            />
          </DialogBody>
        </DialogContent>
      </DialogRoot>
    </Container>
  )
}
