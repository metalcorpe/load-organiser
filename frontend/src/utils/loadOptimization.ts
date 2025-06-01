export interface Jumper {
  id: string
  name: string
  jumpType: "tandem" | "aff" | "fun_jump" | "coach_jump"
  experienceLevel: "beginner" | "intermediate" | "advanced" | "expert"
  weight: number
  exitAltitude: number
  fallRate?: number
  requiresInstructor?: boolean
  instructorId?: string
}

export interface OptimizedLoad {
  exitOrder: Jumper[]
  groups: JumpGroup[]
  totalTime: number
  recommendations: string[]
}

export interface JumpGroup {
  jumpers: Jumper[]
  exitAltitude: number
  groupType: string
  estimatedTime: number
}

/**
 * Calculate optimal exit order based on fall rates and group requirements
 */
export function calculateExitOrder(jumpers: Jumper[]): OptimizedLoad {
  // Sort jumpers by multiple criteria for optimal exit order
  const sortedJumpers = [...jumpers].sort((a, b) => {
    // 1. Tandems go first (lowest exit altitude, slowest fall rate)
    if (a.jumpType === "tandem" && b.jumpType !== "tandem") return -1
    if (b.jumpType === "tandem" && a.jumpType !== "tandem") return 1

    // 2. AFF students next (need clear airspace)
    if (a.jumpType === "aff" && b.jumpType !== "aff" && b.jumpType !== "tandem")
      return -1
    if (b.jumpType === "aff" && a.jumpType !== "aff" && a.jumpType !== "tandem")
      return 1

    // 3. Within same type, sort by experience level and fall rate
    if (a.jumpType === b.jumpType) {
      // Higher exit altitude first
      if (a.exitAltitude !== b.exitAltitude) {
        return b.exitAltitude - a.exitAltitude
      }

      // Slower fall rate first to avoid collision
      const aFallRate = a.fallRate || getDefaultFallRate(a)
      const bFallRate = b.fallRate || getDefaultFallRate(b)
      return aFallRate - bFallRate
    }

    return 0
  })

  // Group jumpers by type and exit altitude
  const groups = createJumpGroups(sortedJumpers)

  // Calculate timing and recommendations
  const totalTime = calculateTotalTime(groups)
  const recommendations = generateRecommendations(groups, jumpers)

  return {
    exitOrder: sortedJumpers,
    groups,
    totalTime,
    recommendations,
  }
}

/**
 * Get default fall rate based on jump type and experience
 */
function getDefaultFallRate(jumper: Jumper): number {
  switch (jumper.jumpType) {
    case "tandem":
      return 120 // mph - slower due to larger surface area
    case "aff":
      return 110 // mph - students fall slower
    case "fun_jump":
      return jumper.experienceLevel === "expert" ? 140 : 130 // mph
    case "coach_jump":
      return 125 // mph - controlled fall rate
    default:
      return 130 // mph
  }
}

/**
 * Create logical jump groups for efficient aircraft operations
 */
function createJumpGroups(jumpers: Jumper[]): JumpGroup[] {
  const groups: JumpGroup[] = []
  let currentGroup: Jumper[] = []
  let currentAltitude = 0
  let currentType = ""

  for (const jumper of jumpers) {
    const groupKey = `${jumper.jumpType}-${jumper.exitAltitude}`

    // Start new group if type/altitude changes significantly
    if (currentType !== groupKey || currentGroup.length >= 8) {
      if (currentGroup.length > 0) {
        groups.push({
          jumpers: [...currentGroup],
          exitAltitude: currentAltitude,
          groupType: currentType,
          estimatedTime: calculateGroupTime(currentGroup),
        })
      }

      currentGroup = [jumper]
      currentAltitude = jumper.exitAltitude
      currentType = groupKey
    } else {
      currentGroup.push(jumper)
    }
  }

  // Add final group
  if (currentGroup.length > 0) {
    groups.push({
      jumpers: currentGroup,
      exitAltitude: currentAltitude,
      groupType: currentType,
      estimatedTime: calculateGroupTime(currentGroup),
    })
  }

  return groups
}

/**
 * Calculate time between groups (includes aircraft positioning)
 */
function calculateGroupTime(jumpers: Jumper[]): number {
  const baseTime = 60 // 60 seconds base time between groups
  const perJumperTime = 10 // 10 seconds per additional jumper

  return baseTime + (jumpers.length - 1) * perJumperTime
}

/**
 * Calculate total load time from takeoff to all jumpers out
 */
function calculateTotalTime(groups: JumpGroup[]): number {
  const climbTime = 20 * 60 // 20 minutes to reach jump altitude
  const groupTimes = groups.reduce(
    (total, group) => total + group.estimatedTime,
    0,
  )
  const transitionTime = (groups.length - 1) * 30 // 30 seconds between altitude changes

  return climbTime + groupTimes + transitionTime
}

/**
 * Generate optimization recommendations
 */
function generateRecommendations(
  groups: JumpGroup[],
  allJumpers: Jumper[],
): string[] {
  const recommendations: string[] = []

  // Check for optimal load composition
  const tandemCount = allJumpers.filter((j) => j.jumpType === "tandem").length
  const affCount = allJumpers.filter((j) => j.jumpType === "aff").length
  // const funJumpCount = allJumpers.filter(j => j.jumpType === 'fun_jump').length;

  if (tandemCount > 6) {
    recommendations.push(
      "Consider splitting tandems across multiple loads for safety",
    )
  }

  if (affCount > 4) {
    recommendations.push(
      "High number of AFF students - ensure adequate instructor coverage",
    )
  }

  if (groups.length > 5) {
    recommendations.push(
      "Multiple altitude changes - consider consolidating groups",
    )
  }

  // Check for instructor requirements
  const instructorRequiredJumpers = allJumpers.filter(
    (j) => j.requiresInstructor,
  )
  const uniqueInstructors = new Set(
    instructorRequiredJumpers.map((j) => j.instructorId),
  )

  if (instructorRequiredJumpers.length > uniqueInstructors.size * 2) {
    recommendations.push(
      "Instructor capacity may be exceeded - consider additional instructors",
    )
  }

  // Weight and balance recommendations
  const totalWeight = allJumpers.reduce((sum, j) => sum + j.weight, 0)
  const avgWeight = totalWeight / allJumpers.length

  if (avgWeight > 200) {
    recommendations.push(
      "Heavy load - verify aircraft weight and balance limits",
    )
  }

  return recommendations
}

/**
 * Optimize aircraft capacity utilization
 */
export function optimizeCapacity(
  availableSlots: number,
  potentialJumpers: Jumper[],
): {
  selectedJumpers: Jumper[]
  waitingList: Jumper[]
  utilizationScore: number
} {
  // Prioritize jumpers by importance and profitability
  const prioritizedJumpers = [...potentialJumpers].sort((a, b) => {
    const aPriority = getJumperPriority(a)
    const bPriority = getJumperPriority(b)
    return bPriority - aPriority
  })

  const selectedJumpers = prioritizedJumpers.slice(0, availableSlots)
  const waitingList = prioritizedJumpers.slice(availableSlots)

  const utilizationScore = (selectedJumpers.length / availableSlots) * 100

  return {
    selectedJumpers,
    waitingList,
    utilizationScore,
  }
}

/**
 * Calculate jumper priority for load optimization
 */
function getJumperPriority(jumper: Jumper): number {
  let priority = 0

  // Base priority by jump type (revenue consideration)
  switch (jumper.jumpType) {
    case "tandem":
      priority += 100 // Highest revenue
      break
    case "aff":
      priority += 80 // Good revenue, training progression
      break
    case "coach_jump":
      priority += 60 // Skill development
      break
    case "fun_jump":
      priority += 40 // Lower revenue but volume
      break
  }

  // Bonus for requiring instructor (helps utilization)
  if (jumper.requiresInstructor) {
    priority += 20
  }

  // Experience level consideration
  switch (jumper.experienceLevel) {
    case "beginner":
      priority += 15 // Need practice
      break
    case "intermediate":
      priority += 10
      break
    case "advanced":
      priority += 5
      break
    case "expert":
      priority += 0 // Can wait
      break
  }

  return priority
}
