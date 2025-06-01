import {
  Box,
  Button,
  Container,
  Flex,
  HStack,
  Heading,
  SimpleGrid,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FiCalendar, FiCloud, FiTruck, FiUser } from "react-icons/fi"

import {
  AircraftService,
  InstructorsService,
  LoadsService,
  WeatherService,
} from "@/client"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  // Fetch data for dashboard stats
  const { data: loadsResponse } = useQuery({
    queryKey: ["loads"],
    queryFn: () => LoadsService.readLoads({}),
  })

  const { data: aircraftResponse } = useQuery({
    queryKey: ["aircraft"],
    queryFn: () => AircraftService.readAircraft({}),
  })

  const { data: instructorsResponse } = useQuery({
    queryKey: ["instructors"],
    queryFn: () => InstructorsService.readInstructors({}),
  })

  const { data: weatherResponse } = useQuery({
    queryKey: ["weather"],
    queryFn: () => WeatherService.readWeatherReports({}),
  })

  // Calculate stats
  const loads = loadsResponse?.data || []
  const aircraft = aircraftResponse || []
  const instructors = instructorsResponse?.data || []
  const weatherReports = weatherResponse?.data || []

  const totalLoads = loads.length
  const activeLoads = loads.filter(
    (load) => load.status === "confirmed" || load.status === "boarded",
  ).length
  const availableAircraft = aircraft.filter((ac: any) => ac.is_active).length
  const activeInstructors = instructors.filter(
    (inst: any) => inst.is_active,
  ).length

  // Get latest weather
  const latestWeather = weatherReports[0]
  const isWeatherSuitable =
    latestWeather?.suitable_for_tandems &&
    latestWeather?.suitable_for_students &&
    latestWeather?.suitable_for_fun_jumpers

  return (
    <Container maxW="full">
      <VStack gap={6} align="stretch">
        {/* Welcome Header */}
        <Box pt={6}>
          <Heading size="lg" mb={2}>
            Skydiving Load Organizer
          </Heading>
          <Text fontSize="lg" color="gray.600">
            Welcome back, {currentUser?.full_name || currentUser?.email} 👋
          </Text>
          <Text color="gray.500">
            Manage your skydiving operations efficiently
          </Text>
        </Box>

        {/* Quick Stats Grid */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6}>
          <Box
            p={6}
            bg="white"
            borderRadius="lg"
            borderWidth="1px"
            borderColor="gray.200"
          >
            <VStack align="start" gap={2}>
              <Flex align="center" gap={3}>
                <FiCalendar size={24} color="blue" />
                <Text fontSize="sm" color="gray.600">
                  Total Loads Today
                </Text>
              </Flex>
              <Text fontSize="2xl" fontWeight="bold">
                {totalLoads}
              </Text>
              <Text fontSize="sm" color="gray.500">
                {activeLoads} active
              </Text>
            </VStack>
          </Box>

          <Box
            p={6}
            bg="white"
            borderRadius="lg"
            borderWidth="1px"
            borderColor="gray.200"
          >
            <VStack align="start" gap={2}>
              <Flex align="center" gap={3}>
                <FiTruck size={24} color="green" />
                <Text fontSize="sm" color="gray.600">
                  Available Aircraft
                </Text>
              </Flex>
              <Text fontSize="2xl" fontWeight="bold">
                {availableAircraft}
              </Text>
              <Text fontSize="sm" color="gray.500">
                of {aircraft.length} total
              </Text>
            </VStack>
          </Box>

          <Box
            p={6}
            bg="white"
            borderRadius="lg"
            borderWidth="1px"
            borderColor="gray.200"
          >
            <VStack align="start" gap={2}>
              <Flex align="center" gap={3}>
                <FiUser size={24} color="purple" />
                <Text fontSize="sm" color="gray.600">
                  Active Instructors
                </Text>
              </Flex>
              <Text fontSize="2xl" fontWeight="bold">
                {activeInstructors}
              </Text>
              <Text fontSize="sm" color="gray.500">
                Ready for assignments
              </Text>
            </VStack>
          </Box>

          <Box
            p={6}
            bg="white"
            borderRadius="lg"
            borderWidth="1px"
            borderColor="gray.200"
          >
            <VStack align="start" gap={2}>
              <Flex align="center" gap={3}>
                <FiCloud
                  size={24}
                  color={isWeatherSuitable ? "green" : "red"}
                />
                <Text fontSize="sm" color="gray.600">
                  Weather Status
                </Text>
              </Flex>
              <Text
                fontSize="lg"
                fontWeight="bold"
                color={isWeatherSuitable ? "green.500" : "red.500"}
              >
                {isWeatherSuitable ? "SUITABLE" : "CHECK CONDITIONS"}
              </Text>
              <Text fontSize="sm" color="gray.500">
                {latestWeather?.wind_speed || 0} mph winds
              </Text>
            </VStack>
          </Box>
        </SimpleGrid>

        {/* Quick Actions */}
        <Box
          p={6}
          bg="white"
          borderRadius="lg"
          borderWidth="1px"
          borderColor="gray.200"
        >
          <Heading size="md" mb={4}>
            Quick Actions
          </Heading>
          <HStack gap={4} flexWrap="wrap">
            <Button colorScheme="blue">
              <FiCalendar style={{ marginRight: "8px" }} />
              Create New Load
            </Button>
            <Button colorScheme="green">
              <FiTruck style={{ marginRight: "8px" }} />
              Manage Aircraft
            </Button>
            <Button colorScheme="purple">
              <FiUser style={{ marginRight: "8px" }} />
              View Instructors
            </Button>
            <Button colorScheme="orange">
              <FiCloud style={{ marginRight: "8px" }} />
              Check Weather
            </Button>
          </HStack>
        </Box>

        {/* Recent Activity */}
        <Box
          p={6}
          bg="white"
          borderRadius="lg"
          borderWidth="1px"
          borderColor="gray.200"
        >
          <Heading size="md" mb={4}>
            Recent Loads
          </Heading>
          {loads.slice(0, 5).map((load, index) => (
            <Box
              key={load.id}
              p={3}
              borderBottom="1px"
              borderColor="gray.200"
              _last={{ borderBottom: "none" }}
            >
              <HStack justify="space-between">
                <VStack align="start" gap={1}>
                  <Text fontWeight="semibold">Load #{index + 1}</Text>
                  <Text fontSize="sm" color="gray.500">
                    {new Date(load.scheduled_time).toLocaleTimeString()} -{" "}
                    {load.aircraft.model}
                  </Text>
                </VStack>
                <Text
                  fontSize="sm"
                  px={2}
                  py={1}
                  borderRadius="md"
                  bg={
                    load.status === "confirmed"
                      ? "green.100"
                      : load.status === "completed"
                        ? "blue.100"
                        : load.status === "cancelled"
                          ? "red.100"
                          : "gray.100"
                  }
                  color={
                    load.status === "confirmed"
                      ? "green.800"
                      : load.status === "completed"
                        ? "blue.800"
                        : load.status === "cancelled"
                          ? "red.800"
                          : "gray.800"
                  }
                >
                  {load.status}
                </Text>
              </HStack>
            </Box>
          ))}
          {loads.length === 0 && (
            <Text color="gray.500" textAlign="center" py={4}>
              No loads found. Create your first load to get started!
            </Text>
          )}
        </Box>
      </VStack>
    </Container>
  )
}
