import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Flex,
  HStack,
  Heading,
  Icon,
  List,
  ListItem,
  ProgressRoot,
  ProgressValueText,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useState } from "react"
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiTrendingUp,
  FiUsers,
} from "react-icons/fi"

import {
  type Jumper,
  type OptimizedLoad,
  calculateExitOrder,
} from "../../utils/loadOptimization"

interface LoadOptimizerProps {
  loadId: string
  aircraftCapacity: number
  currentJumpers: any[] // Replace with actual jumper type
  onOptimizationApplied: (optimization: OptimizedLoad) => void
}

export function LoadOptimizer({
  aircraftCapacity,
  currentJumpers,
  onOptimizationApplied,
}: LoadOptimizerProps) {
  const [optimization, setOptimization] = useState<OptimizedLoad | null>(null)
  const [isOptimizing, setIsOptimizing] = useState(false)

  // Convert current jumpers to optimization format
  const convertToOptimizationFormat = (jumpers: any[]): Jumper[] => {
    return jumpers.map((jumper, index) => ({
      id: jumper.id || `jumper-${index}`,
      name: jumper.jumper_name || `Jumper ${index + 1}`,
      jumpType: jumper.jump_type || "fun_jump",
      experienceLevel: jumper.experience_level || "intermediate",
      weight: jumper.weight || 180,
      exitAltitude: jumper.exit_altitude || 14000,
      fallRate: jumper.fall_rate,
      requiresInstructor:
        jumper.jump_type === "tandem" || jumper.jump_type === "aff",
      instructorId: jumper.instructor_id,
    }))
  }

  const runOptimization = async () => {
    setIsOptimizing(true)

    try {
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 1000))

      const jumpersData = convertToOptimizationFormat(currentJumpers)
      const optimizedLoad = calculateExitOrder(jumpersData)

      setOptimization(optimizedLoad)
    } finally {
      setIsOptimizing(false)
    }
  }

  const applyOptimization = () => {
    if (optimization) {
      onOptimizationApplied(optimization)
    }
  }

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

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`
  }

  return (
    <Card.Root>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Load Optimization</Heading>
          <Button
            colorScheme="blue"
            onClick={runOptimization}
            loading={isOptimizing}
            loadingText="Optimizing..."
          >
            <Icon as={FiTrendingUp} mr={2} />
            Optimize Load
          </Button>
        </Flex>
      </CardHeader>

      <CardBody>
        {!optimization ? (
          <VStack gap={4} py={8} color="gray.500">
            <Icon as={FiUsers} boxSize={12} />
            <Text textAlign="center">
              Click "Optimize Load" to calculate the optimal exit order and
              receive recommendations for this load.
            </Text>
          </VStack>
        ) : (
          <VStack gap={6} align="stretch">
            {/* Optimization Summary */}
            <Box>
              <Heading size="sm" mb={3}>
                Optimization Summary
              </Heading>
              <HStack gap={6}>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold">
                    {optimization.exitOrder.length}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Jumpers
                  </Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold">
                    {optimization.groups.length}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Groups
                  </Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold">
                    {formatTime(optimization.totalTime)}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Total Time
                  </Text>
                </VStack>
              </HStack>
            </Box>

            <Separator />

            {/* Exit Order */}
            <Box>
              <Heading size="sm" mb={3}>
                Optimized Exit Order
              </Heading>
              <VStack gap={2} align="stretch">
                {optimization.exitOrder.map((jumper, index) => (
                  <Flex
                    key={jumper.id}
                    justify="space-between"
                    align="center"
                    p={3}
                    bg="gray.50"
                    borderRadius="md"
                  >
                    <HStack>
                      <Text fontWeight="medium" w="8">
                        #{index + 1}
                      </Text>
                      <Text>{jumper.name}</Text>
                      <Badge colorScheme={getJumpTypeColor(jumper.jumpType)}>
                        {jumper.jumpType.toUpperCase()}
                      </Badge>
                    </HStack>
                    <VStack gap={0} align="end">
                      <Text fontSize="sm">{jumper.exitAltitude} ft</Text>
                      <Text fontSize="xs" color="gray.500">
                        {jumper.fallRate || "Est."} mph
                      </Text>
                    </VStack>
                  </Flex>
                ))}
              </VStack>
            </Box>

            <Separator />

            {/* Jump Groups */}
            <Box>
              <Heading size="sm" mb={3}>
                Jump Groups
              </Heading>
              <VStack gap={3} align="stretch">
                {optimization.groups.map((group, index) => (
                  <Card.Root key={index} variant="outline">
                    <CardBody p={4}>
                      <Flex justify="space-between" align="center" mb={2}>
                        <Text fontWeight="medium">
                          Group {index + 1} - {group.groupType}
                        </Text>
                        <Badge colorScheme="blue">
                          {formatTime(group.estimatedTime)}
                        </Badge>
                      </Flex>
                      <Text fontSize="sm" color="gray.600" mb={2}>
                        {group.jumpers.length} jumpers at {group.exitAltitude}{" "}
                        ft
                      </Text>
                      <Text fontSize="sm">
                        {group.jumpers.map((j) => j.name).join(", ")}
                      </Text>
                    </CardBody>
                  </Card.Root>
                ))}
              </VStack>
            </Box>

            <Separator />

            {/* Recommendations */}
            <Box>
              <Heading size="sm" mb={3}>
                Recommendations
              </Heading>
              {optimization.recommendations.length > 0 ? (
                <List.Root gap={2}>
                  {optimization.recommendations.map((rec, index) => (
                    <ListItem key={index}>
                      <HStack>
                        <Icon as={FiAlertTriangle} color="orange.500" />
                        <Text fontSize="sm">{rec}</Text>
                      </HStack>
                    </ListItem>
                  ))}
                </List.Root>
              ) : (
                <HStack>
                  <Icon as={FiCheckCircle} color="green.500" />
                  <Text fontSize="sm" color="green.600">
                    Load is optimally configured with no issues detected.
                  </Text>
                </HStack>
              )}
            </Box>

            {/* Capacity Utilization */}
            <Box>
              <Heading size="sm" mb={3}>
                Capacity Utilization
              </Heading>
              <VStack gap={2} align="stretch">
                <Flex justify="space-between">
                  <Text fontSize="sm">
                    {optimization.exitOrder.length} / {aircraftCapacity} slots
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {Math.round(
                      (optimization.exitOrder.length / aircraftCapacity) * 100,
                    )}
                    %
                  </Text>
                </Flex>
                <ProgressRoot
                  value={
                    (optimization.exitOrder.length / aircraftCapacity) * 100
                  }
                  colorScheme="blue"
                  size="sm"
                >
                  <ProgressValueText />
                </ProgressRoot>
              </VStack>
            </Box>

            {/* Action Buttons */}
            <HStack gap={3} pt={4}>
              <Button variant="outline" onClick={() => setOptimization(null)}>
                Reset
              </Button>
              <Button colorScheme="green" onClick={applyOptimization}>
                <Icon as={FiCheckCircle} mr={2} />
                Apply Optimization
              </Button>
            </HStack>
          </VStack>
        )}
      </CardBody>
    </Card.Root>
  )
}
