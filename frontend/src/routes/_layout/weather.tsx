import {
  Badge,
  Box,
  Button,
  Container,
  Flex,
  HStack,
  Heading,
  Separator,
  SimpleGrid,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  FiCloud,
  FiCloudRain,
  FiEye,
  FiRefreshCw,
  FiSun,
  FiThermometer,
  FiWind,
} from "react-icons/fi"

import { WeatherService } from "@/client"
import type { WeatherReportPublic } from "@/client"

export const Route = createFileRoute("/_layout/weather")({
  component: WeatherPage,
})

function WeatherPage() {
  const {
    data: weatherResponse,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["weather"],
    queryFn: () => WeatherService.readWeatherReports({}),
  })

  const weatherReports = weatherResponse?.data || []
  const latestWeather = weatherReports[0]

  const getWindCondition = (windSpeed: number) => {
    if (windSpeed <= 10) return { color: "green", text: "Excellent" }
    if (windSpeed <= 15) return { color: "yellow", text: "Good" }
    if (windSpeed <= 20) return { color: "orange", text: "Marginal" }
    return { color: "red", text: "Poor" }
  }

  const getVisibilityCondition = (visibility: number) => {
    if (visibility >= 10) return { color: "green", text: "Excellent" }
    if (visibility >= 5) return { color: "yellow", text: "Good" }
    if (visibility >= 3) return { color: "orange", text: "Marginal" }
    return { color: "red", text: "Poor" }
  }

  const getCeilingCondition = (ceiling: number) => {
    if (ceiling >= 5000) return { color: "green", text: "Excellent" }
    if (ceiling >= 3000) return { color: "yellow", text: "Good" }
    if (ceiling >= 2000) return { color: "orange", text: "Marginal" }
    return { color: "red", text: "Poor" }
  }

  const windCondition = latestWeather
    ? getWindCondition(latestWeather.wind_speed)
    : null
  const visibilityCondition = latestWeather
    ? getVisibilityCondition(latestWeather.visibility)
    : null
  const ceilingCondition =
    latestWeather && latestWeather.cloud_ceiling != null
      ? getCeilingCondition(latestWeather.cloud_ceiling)
      : null

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg">Weather Conditions</Heading>
            <Text color="gray.600">
              Current conditions for skydiving operations
            </Text>
          </Box>
          <Button colorScheme="blue" onClick={() => refetch()}>
            <FiRefreshCw style={{ marginRight: "8px" }} />
            Refresh Weather
          </Button>
        </Flex>

        <Separator />

        {isLoading ? (
          <Box textAlign="center" py={10}>
            <Text>Loading weather data...</Text>
          </Box>
        ) : !latestWeather ? (
          <Box textAlign="center" py={10}>
            <Text color="gray.500" mb={4}>
              No weather data available
            </Text>
            <Button colorScheme="blue" onClick={() => refetch()}>
              <FiRefreshCw style={{ marginRight: "8px" }} />
              Load Weather Data
            </Button>
          </Box>
        ) : (
          <>
            {/* Current Conditions Summary */}
            <Box p={6} bg="white" borderRadius="lg" borderWidth="1px">
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Current Conditions</Heading>
                <Text fontSize="sm" color="gray.500">
                  Last updated:{" "}
                  {new Date(latestWeather.created_at).toLocaleString()}
                </Text>
              </HStack>

              <SimpleGrid columns={{ base: 1, md: 3 }} gap={6}>
                {/* Overall Suitability */}
                <Box textAlign="center">
                  <VStack gap={3}>
                    <Box fontSize="4xl">
                      {latestWeather.suitable_for_tandems &&
                      latestWeather.suitable_for_students &&
                      latestWeather.suitable_for_fun_jumpers ? (
                        <FiSun color="green" />
                      ) : (
                        <FiCloudRain color="red" />
                      )}
                    </Box>
                    <VStack gap={1}>
                      <Text fontWeight="bold" fontSize="lg">
                        {latestWeather.suitable_for_tandems &&
                        latestWeather.suitable_for_students &&
                        latestWeather.suitable_for_fun_jumpers
                          ? "SUITABLE FOR JUMPING"
                          : "NOT SUITABLE"}
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        Overall assessment
                      </Text>
                    </VStack>
                  </VStack>
                </Box>

                {/* Temperature */}
                <Box textAlign="center">
                  <VStack gap={3}>
                    <Box fontSize="4xl">
                      <FiThermometer color="orange" />
                    </Box>
                    <VStack gap={1}>
                      <Text fontWeight="bold" fontSize="2xl">
                        {22}°F
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        Ground temperature
                      </Text>
                    </VStack>
                  </VStack>
                </Box>

                {/* Wind Speed */}
                <Box textAlign="center">
                  <VStack gap={3}>
                    <Box fontSize="4xl">
                      <FiWind color={windCondition?.color} />
                    </Box>
                    <VStack gap={1}>
                      <Text fontWeight="bold" fontSize="2xl">
                        {latestWeather.wind_speed} mph
                      </Text>
                      <Badge colorScheme={windCondition?.color} fontSize="sm">
                        {windCondition?.text}
                      </Badge>
                    </VStack>
                  </VStack>
                </Box>
              </SimpleGrid>
            </Box>

            {/* Detailed Conditions */}
            <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
              {/* Visibility */}
              <Box p={6} bg="white" borderRadius="lg" borderWidth="1px">
                <HStack justify="space-between" mb={4}>
                  <HStack>
                    <FiEye />
                    <Heading size="sm">Visibility</Heading>
                  </HStack>
                  <Badge colorScheme={visibilityCondition?.color}>
                    {visibilityCondition?.text}
                  </Badge>
                </HStack>
                <Text fontSize="2xl" fontWeight="bold" mb={2}>
                  {latestWeather.visibility} miles
                </Text>
                {/* <Progress 
                  value={Math.min((latestWeather.visibility / 15) * 100, 100)} 
                  colorScheme={visibilityCondition?.color}
                  size="sm"
                /> */}
                <Text fontSize="sm" color="gray.600" mt={2}>
                  Minimum required: 3 miles
                </Text>
              </Box>

              {/* Ceiling */}
              <Box p={6} bg="white" borderRadius="lg" borderWidth="1px">
                <HStack justify="space-between" mb={4}>
                  <HStack>
                    <FiCloud />
                    <Heading size="sm">Cloud Ceiling</Heading>
                  </HStack>
                  <Badge colorScheme={ceilingCondition?.color}>
                    {ceilingCondition?.text}
                  </Badge>
                </HStack>
                {/* <Text fontSize="2xl" fontWeight="bold" mb={2}>
                  {latestWeather.ceiling.toLocaleString()} ft
                </Text> */}
                {/* <Progress 
                  value={Math.min((latestWeather.ceiling / 10000) * 100, 100)} 
                  colorScheme={ceilingCondition?.color}
                  size="sm"
                /> */}
                <Text fontSize="sm" color="gray.600" mt={2}>
                  Minimum required: 2,000 ft
                </Text>
              </Box>
            </SimpleGrid>

            {/* Jump Type Suitability */}
            <Box p={6} bg="white" borderRadius="lg" borderWidth="1px">
              <Heading size="md" mb={4}>
                Jump Type Suitability
              </Heading>
              <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
                <Box
                  p={4}
                  borderRadius="md"
                  bg={
                    latestWeather.suitable_for_tandems ? "green.50" : "red.50"
                  }
                >
                  <HStack justify="space-between" mb={2}>
                    <Text fontWeight="semibold">Tandem Jumps</Text>
                    <Badge
                      colorScheme={
                        latestWeather.suitable_for_tandems ? "green" : "red"
                      }
                    >
                      {latestWeather.suitable_for_tandems
                        ? "SUITABLE"
                        : "NOT SUITABLE"}
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color="gray.600">
                    First-time jumps with instructor
                  </Text>
                </Box>

                <Box
                  p={4}
                  borderRadius="md"
                  bg={
                    latestWeather.suitable_for_students ? "green.50" : "red.50"
                  }
                >
                  <HStack justify="space-between" mb={2}>
                    <Text fontWeight="semibold">Student Jumps</Text>
                    <Badge
                      colorScheme={
                        latestWeather.suitable_for_students ? "green" : "red"
                      }
                    >
                      {latestWeather.suitable_for_students
                        ? "SUITABLE"
                        : "NOT SUITABLE"}
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color="gray.600">
                    AFF and training jumps
                  </Text>
                </Box>

                <Box
                  p={4}
                  borderRadius="md"
                  bg={
                    latestWeather.suitable_for_fun_jumpers
                      ? "green.50"
                      : "red.50"
                  }
                >
                  <HStack justify="space-between" mb={2}>
                    <Text fontWeight="semibold">Fun Jumps</Text>
                    <Badge
                      colorScheme={
                        latestWeather.suitable_for_fun_jumpers ? "green" : "red"
                      }
                    >
                      {latestWeather.suitable_for_fun_jumpers
                        ? "SUITABLE"
                        : "NOT SUITABLE"}
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color="gray.600">
                    Experienced skydivers
                  </Text>
                </Box>
              </SimpleGrid>
            </Box>

            {/* Weather History */}
            {weatherReports.length > 1 && (
              <Box p={6} bg="white" borderRadius="lg" borderWidth="1px">
                <Heading size="md" mb={4}>
                  Recent Weather History
                </Heading>
                <VStack gap={3}>
                  {weatherReports
                    .slice(1, 6)
                    .map((report: WeatherReportPublic) => (
                      <Box
                        key={report.id}
                        w="full"
                        p={3}
                        borderRadius="md"
                        bg="gray.50"
                      >
                        <HStack justify="space-between">
                          <Text fontSize="sm" fontWeight="semibold">
                            {new Date(report.created_at).toLocaleString()}
                          </Text>
                          <HStack gap={4}>
                            <Text fontSize="sm">
                              {report.wind_speed} mph winds
                            </Text>
                            <Text fontSize="sm">
                              {report.visibility} mi vis
                            </Text>
                            <Text fontSize="sm">{22}°F</Text>
                            <Badge
                              size="sm"
                              colorScheme={
                                report.suitable_for_tandems &&
                                report.suitable_for_students &&
                                report.suitable_for_fun_jumpers
                                  ? "green"
                                  : "red"
                              }
                            >
                              {report.suitable_for_tandems &&
                              report.suitable_for_students &&
                              report.suitable_for_fun_jumpers
                                ? "OK"
                                : "NO"}
                            </Badge>
                          </HStack>
                        </HStack>
                      </Box>
                    ))}
                </VStack>
              </Box>
            )}
          </>
        )}
      </VStack>
    </Container>
  )
}
