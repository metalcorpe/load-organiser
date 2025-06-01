import {
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
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  FiCheckCircle,
  FiEdit,
  FiPlus,
  FiTrash2,
  FiTruck,
  FiXCircle,
} from "react-icons/fi"

import { AircraftService } from "../../client"
import type { AircraftPublic } from "../../client"
import { AircraftForm } from "../../components/Forms/AircraftForm"
import {
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "../../components/ui/dialog"

export const Route = createFileRoute("/_layout/aircraft")({
  component: AircraftPage,
})

function AircraftPage() {
  const queryClient = useQueryClient()
  const [selectedAircraft, setSelectedAircraft] =
    useState<AircraftPublic | null>(null)
  const { open: isOpen, onOpen, onClose } = useDisclosure()

  const { data: aircraft, isLoading } = useQuery({
    queryKey: ["aircraft"],
    queryFn: () => AircraftService.readAircraft({}),
  })

  const deleteAircraftMutation = useMutation({
    mutationFn: (aircraftId: string) =>
      AircraftService.deleteAircraft({ id: aircraftId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aircraft"] })
    },
  })

  const toggleAircraftStatusMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      AircraftService.updateAircraft({
        id,
        requestBody: { is_active: !isActive },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aircraft"] })
    },
  })

  const aircraftList = aircraft || []
  const activeAircraft = aircraftList.filter(
    (ac: AircraftPublic) => ac.is_active,
  )
  const totalCapacity = aircraftList.reduce(
    (sum: number, ac: AircraftPublic) =>
      ac.is_active ? sum + ac.capacity : sum,
    0,
  )

  const handleDeleteAircraft = (aircraftId: string) => {
    if (window.confirm("Are you sure you want to delete this aircraft?")) {
      deleteAircraftMutation.mutate(aircraftId)
    }
  }

  const handleEditAircraft = (aircraft: AircraftPublic) => {
    setSelectedAircraft(aircraft)
    onOpen()
  }

  const handleCreateAircraft = () => {
    setSelectedAircraft(null)
    onOpen()
  }

  const handleToggleStatus = (aircraft: AircraftPublic) => {
    toggleAircraftStatusMutation.mutate({
      id: aircraft.id,
      isActive: aircraft.is_active || false,
    })
  }

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg">Aircraft Management</Heading>
            <Text color="gray.600">Manage your fleet of aircraft</Text>
          </Box>
          <Button colorScheme="blue" size="lg" onClick={handleCreateAircraft}>
            <FiPlus style={{ marginRight: "8px" }} />
            Add New Aircraft
          </Button>
        </Flex>

        <Separator />

        {/* Stats Summary */}
        <SimpleGrid columns={{ base: 1, md: 4 }} gap={4}>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiTruck color="blue" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Total Aircraft
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {aircraftList.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiCheckCircle color="green" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Active Aircraft
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {activeAircraft.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiXCircle color="red" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Inactive Aircraft
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {aircraftList.length - activeAircraft.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <VStack align="start" gap={0}>
              <Text fontSize="sm" color="gray.600">
                Total Capacity
              </Text>
              <Text fontSize="2xl" fontWeight="bold">
                {totalCapacity}
              </Text>
              <Text fontSize="xs" color="gray.500">
                active aircraft only
              </Text>
            </VStack>
          </Box>
        </SimpleGrid>

        {/* Aircraft Table */}
        <Box bg="white" borderRadius="lg" borderWidth="1px" overflow="hidden">
          <Box p={4} borderBottom="1px" borderColor="gray.200">
            <Heading size="md">Aircraft Fleet</Heading>
          </Box>

          {isLoading ? (
            <Box p={8} textAlign="center">
              <Text>Loading aircraft...</Text>
            </Box>
          ) : aircraftList.length === 0 ? (
            <Box p={8} textAlign="center">
              <Text color="gray.500" mb={4}>
                No aircraft registered yet
              </Text>
              <Button colorScheme="blue" onClick={handleCreateAircraft}>
                <FiPlus style={{ marginRight: "8px" }} />
                Add First Aircraft
              </Button>
            </Box>
          ) : (
            <Table.Root size={{ base: "sm", md: "md" }}>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>Registration</Table.ColumnHeader>
                  <Table.ColumnHeader>Model</Table.ColumnHeader>
                  <Table.ColumnHeader>Capacity</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {aircraftList.map((aircraft: AircraftPublic) => (
                  <Table.Row key={aircraft.id}>
                    <Table.Cell fontWeight="semibold">
                      {aircraft.registration}
                    </Table.Cell>
                    <Table.Cell>{aircraft.model}</Table.Cell>
                    <Table.Cell>{aircraft.capacity} passengers</Table.Cell>
                    <Table.Cell>
                      <Badge
                        colorScheme={aircraft.is_active ? "green" : "red"}
                        variant="subtle"
                      >
                        {aircraft.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <HStack gap={2}>
                        <IconButton
                          aria-label="Edit aircraft"
                          size="sm"
                          variant="ghost"
                          colorScheme="blue"
                          onClick={() => handleEditAircraft(aircraft)}
                        >
                          <FiEdit />
                        </IconButton>
                        <Button
                          size="sm"
                          variant="ghost"
                          colorScheme={aircraft.is_active ? "red" : "green"}
                          onClick={() => handleToggleStatus(aircraft)}
                        >
                          {aircraft.is_active ? "Deactivate" : "Activate"}
                        </Button>
                        <IconButton
                          aria-label="Delete aircraft"
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => handleDeleteAircraft(aircraft.id)}
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
              Add Aircraft
            </Button>
            <Button size="sm" variant="outline">
              Import from CSV
            </Button>
            <Button size="sm" variant="outline">
              Export Fleet Data
            </Button>
            <Button size="sm" variant="outline">
              Maintenance Schedule
            </Button>
          </HStack>
        </Box>
      </VStack>

      {/* Aircraft Form Dialog */}
      <DialogRoot open={isOpen} onOpenChange={onClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedAircraft ? "Edit Aircraft" : "Add New Aircraft"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <AircraftForm
              aircraft={selectedAircraft || undefined}
              onSuccess={() => {
                onClose()
                queryClient.invalidateQueries({ queryKey: ["aircraft"] })
              }}
              onCancel={onClose}
            />
          </DialogBody>
        </DialogContent>
      </DialogRoot>
    </Container>
  )
}
