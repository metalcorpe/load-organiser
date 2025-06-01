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
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  FiClock,
  FiEdit,
  FiPlus,
  FiTrash2,
  FiTrendingUp,
  FiUsers,
} from "react-icons/fi"

import { LoadsService } from "../../client"
import type { LoadPublic } from "../../client"
import { LoadForm } from "../../components/Forms/LoadForm"
import { LoadOptimizer } from "../../components/LoadOptimizer/LoadOptimizer"
import {
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "../../components/ui/dialog"
import useCustomToast from "../../hooks/useCustomToast"

export const Route = createFileRoute("/_layout/loads-backup")({
  component: LoadsPage,
})

function LoadsPage() {
  const queryClient = useQueryClient()
  const [selectedLoad, setSelectedLoad] = useState<LoadPublic | null>(null)
  const [isCreateMode, setIsCreateMode] = useState(false)
  const [showOptimizer, setShowOptimizer] = useState(false)
  const { open: isOpen, onOpen, onClose } = useDisclosure()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: loadsResponse, isLoading: isLoadingLoads } = useQuery({
    queryKey: ["loads"],
    queryFn: () => LoadsService.readLoads({}),
  })

  // const { data: aircraft } = useQuery({
  //   queryKey: ["aircraft"],
  //   queryFn: () => AircraftService.readAircraft({}),
  // })

  const deleteLoadMutation = useMutation({
    mutationFn: (loadId: string) => LoadsService.deleteLoad({ id: loadId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["loads"] })
      showSuccessToast("Load deleted successfully")
    },
    onError: () => {
      showErrorToast("Failed to delete load")
    },
  })

  const loads = loadsResponse?.data || []

  const handleCreateLoad = () => {
    setSelectedLoad(null)
    setIsCreateMode(true)
    setShowOptimizer(false)
    onOpen()
  }

  const handleEditLoad = (load: LoadPublic) => {
    setSelectedLoad(load)
    setIsCreateMode(false)
    setShowOptimizer(false)
    onOpen()
  }

  const handleOptimizeLoad = (load: LoadPublic) => {
    setSelectedLoad(load)
    setShowOptimizer(true)
    onOpen()
  }

  const handleDeleteLoad = (loadId: string) => {
    if (confirm("Are you sure you want to delete this load?")) {
      deleteLoadMutation.mutate(loadId)
    }
  }

  // const getStatusColor = (status: string) => {
  //   switch (status) {
  //     case "planning":
  //       return "gray"
  //     case "confirmed":
  //       return "blue"
  //     case "boarded":
  //       return "yellow"
  //     case "departed":
  //       return "orange"
  //     case "completed":
  //       return "green"
  //     case "cancelled":
  //       return "red"
  //     default:
  //       return "gray"
  //   }
  // }

  const confirmedLoads = loads.filter((load) => load.status === "confirmed")
  const completedLoads = loads.filter((load) => load.status === "completed")
  const totalJumpers = loads.reduce(
    (sum, load) => sum + (load.jumps?.length || 0),
    0,
  )

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg">Load Management</Heading>
            <Text color="gray.600">Organize and track skydiving loads</Text>
          </Box>
          <Button colorScheme="blue" size="lg" onClick={handleCreateLoad}>
            <FiPlus style={{ marginRight: "8px" }} />
            Create New Load
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
                  Total Loads
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {loads.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiClock color="green" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Confirmed Today
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {confirmedLoads.length}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <HStack>
              <FiUsers color="purple" />
              <VStack align="start" gap={0}>
                <Text fontSize="sm" color="gray.600">
                  Total Jumpers
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {totalJumpers}
                </Text>
              </VStack>
            </HStack>
          </Box>
          <Box p={4} bg="white" borderRadius="md" borderWidth="1px">
            <VStack align="start" gap={0}>
              <Text fontSize="sm" color="gray.600">
                Completed
              </Text>
              <Text fontSize="2xl" fontWeight="bold">
                {completedLoads.length}
              </Text>
              <Text fontSize="xs" color="gray.500">
                loads finished
              </Text>
            </VStack>
          </Box>
        </SimpleGrid>

        {/* Loads List */}
        <Box bg="white" borderRadius="lg" borderWidth="1px" overflow="hidden">
          <Box p={4} borderBottom="1px" borderColor="gray.200">
            <Heading size="md">Current Loads</Heading>
          </Box>

          {isLoadingLoads ? (
            <Box p={8} textAlign="center">
              <Text>Loading loads...</Text>
            </Box>
          ) : loads.length === 0 ? (
            <Box p={8} textAlign="center">
              <Text color="gray.500" mb={4}>
                No loads scheduled yet
              </Text>
              <Button colorScheme="blue" onClick={handleCreateLoad}>
                <FiPlus style={{ marginRight: "8px" }} />
                Create First Load
              </Button>
            </Box>
          ) : (
            <VStack gap={0} align="stretch">
              {loads.map((load: LoadPublic) => (
                <LoadCard
                  key={load.id}
                  load={load}
                  onEdit={handleEditLoad}
                  onDelete={handleDeleteLoad}
                  onOptimize={handleOptimizeLoad}
                />
              ))}
            </VStack>
          )}
        </Box>

        {/* Quick Actions */}
        <Box p={6} bg="gray.50" borderRadius="lg">
          <Heading size="sm" mb={3}>
            Quick Actions
          </Heading>
          <HStack gap={3} flexWrap="wrap">
            <Button size="sm" colorScheme="blue">
              Schedule Load
            </Button>
            <Button size="sm" variant="outline">
              Weather Check
            </Button>
            <Button size="sm" variant="outline">
              Manifest Report
            </Button>
            <Button size="sm" variant="outline">
              Daily Summary
            </Button>
          </HStack>
        </Box>
      </VStack>

      {/* Load Form/Optimizer Dialog */}
      <DialogRoot open={isOpen} onOpenChange={onClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {showOptimizer
                ? "Load Optimization"
                : isCreateMode
                  ? "Create New Load"
                  : "Edit Load"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            {showOptimizer && selectedLoad ? (
              <LoadOptimizer
                loadId={selectedLoad.id}
                aircraftCapacity={selectedLoad.aircraft?.capacity || 15}
                currentJumpers={[]} // Would need to get actual jumpers
                onOptimizationApplied={() => {
                  onClose()
                  queryClient.invalidateQueries({ queryKey: ["loads"] })
                }}
              />
            ) : (
              <LoadForm
                load={selectedLoad || undefined}
                onSuccess={() => {
                  onClose()
                  queryClient.invalidateQueries({ queryKey: ["loads"] })
                }}
                onCancel={onClose}
              />
            )}
          </DialogBody>
        </DialogContent>
      </DialogRoot>
    </Container>
  )
}

interface LoadCardProps {
  load: LoadPublic
  onEdit: (load: LoadPublic) => void
  onDelete: (loadId: string) => void
  onOptimize: (load: LoadPublic) => void
}

function LoadCard({ load, onEdit, onDelete, onOptimize }: LoadCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "planning":
        return "gray"
      case "confirmed":
        return "blue"
      case "boarded":
        return "yellow"
      case "departed":
        return "orange"
      case "completed":
        return "green"
      case "cancelled":
        return "red"
      default:
        return "gray"
    }
  }

  return (
    <Box
      p={4}
      borderBottom="1px"
      borderColor="gray.200"
      _last={{ borderBottom: "none" }}
    >
      <Flex justify="space-between" align="start">
        <VStack align="start" gap={2} flex={1}>
          <HStack gap={3}>
            <Text fontWeight="semibold">
              Load #{load.id.slice(-6) || "TBD"}
            </Text>
            <Badge
              colorScheme={getStatusColor(load.status || "planning")}
              variant="subtle"
            >
              {load.status?.toUpperCase() || "PLANNING"}
            </Badge>
            <Text fontSize="sm" color="gray.600">
              {new Date(load.scheduled_time).toLocaleTimeString()} -{" "}
              {load.aircraft?.model || "No Aircraft"}
            </Text>
          </HStack>

          <HStack gap={4}>
            <HStack gap={1}>
              <FiUsers color="gray" />
              <Text fontSize="sm" color="gray.600">
                {load.jumps?.length || 0} / {load.aircraft?.capacity || 15}{" "}
                jumpers
              </Text>
            </HStack>
            <HStack gap={1}>
              <FiClock color="gray" />
              <Text fontSize="sm" color="gray.600">
                {load.altitude || 14000} ft
              </Text>
            </HStack>
          </HStack>

          {load.notes && (
            <Text fontSize="sm" color="gray.500" fontStyle="italic">
              {load.notes}
            </Text>
          )}
        </VStack>

        <HStack gap={2}>
          <IconButton
            aria-label="Optimize load"
            size="sm"
            variant="ghost"
            colorScheme="purple"
            onClick={() => onOptimize(load)}
          >
            <FiTrendingUp />
          </IconButton>
          <IconButton
            aria-label="Edit load"
            size="sm"
            variant="ghost"
            colorScheme="blue"
            onClick={() => onEdit(load)}
          >
            <FiEdit />
          </IconButton>
          <IconButton
            aria-label="Delete load"
            size="sm"
            variant="ghost"
            colorScheme="red"
            onClick={() => onDelete(load.id)}
          >
            <FiTrash2 />
          </IconButton>
        </HStack>
      </Flex>
    </Box>
  )
}
