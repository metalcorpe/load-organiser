import { Button, HStack, Input, VStack } from "@chakra-ui/react"
import { useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { Controller, useForm } from "react-hook-form"

import {
  type AircraftCreate,
  type AircraftPublic,
  AircraftService,
  type AircraftUpdate,
  type ApiError,
} from "../../client"
import { Checkbox } from "../../components/ui/checkbox"
import { Field } from "../../components/ui/field"
import useCustomToast from "../../hooks/useCustomToast"

interface AircraftFormProps {
  aircraft?: AircraftPublic
  onSuccess: () => void
  onCancel: () => void
}

interface AircraftFormData {
  registration: string
  model: string
  capacity: number
  is_active: boolean
}

export function AircraftForm({
  aircraft,
  onSuccess,
  onCancel,
}: AircraftFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<AircraftFormData>({
    defaultValues: {
      registration: aircraft?.registration || "",
      model: aircraft?.model || "",
      capacity: aircraft?.capacity || 12,
      is_active: aircraft?.is_active !== false,
    },
  })

  // Reset form when aircraft changes
  useEffect(() => {
    if (aircraft) {
      reset({
        registration: aircraft.registration || "",
        model: aircraft.model || "",
        capacity: aircraft.capacity || 12,
        is_active: aircraft.is_active !== false,
      })
    }
  }, [aircraft, reset])

  const onSubmit = async (data: AircraftFormData) => {
    try {
      if (aircraft?.id) {
        // Update existing aircraft
        const updateData: AircraftUpdate = {
          registration: data.registration,
          model: data.model,
          capacity: data.capacity,
          is_active: data.is_active,
        }

        await AircraftService.updateAircraft({
          id: aircraft.id,
          requestBody: updateData,
        })

        showSuccessToast("Aircraft updated successfully!")
      } else {
        // Create new aircraft
        const createData: AircraftCreate = {
          registration: data.registration,
          model: data.model,
          capacity: data.capacity,
          is_active: data.is_active,
        }

        await AircraftService.createAircraft({ requestBody: createData })

        showSuccessToast("Aircraft created successfully!")
      }

      queryClient.invalidateQueries({ queryKey: ["aircraft"] })
      onSuccess()
    } catch (error) {
      const apiError = error as ApiError
      const errDetail =
        apiError.body &&
        typeof apiError.body === "object" &&
        "detail" in apiError.body
          ? (apiError.body.detail as string)
          : undefined
      showErrorToast(errDetail || "Something went wrong")
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <VStack gap={4} align="stretch">
        {/* Registration and Model */}
        <HStack gap={4}>
          <Field
            label="Registration"
            invalid={!!errors.registration}
            errorText={errors.registration?.message}
          >
            <Input
              placeholder="e.g., N123AB"
              {...register("registration", {
                required: "Registration is required",
                pattern: {
                  value: /^[A-Z0-9\-]+$/,
                  message: "Use uppercase letters and numbers only",
                },
              })}
            />
          </Field>

          <Field
            label="Model"
            invalid={!!errors.model}
            errorText={errors.model?.message}
          >
            <Input
              placeholder="e.g., Cessna 182"
              {...register("model", {
                required: "Model is required",
              })}
            />
          </Field>
        </HStack>

        {/* Capacity */}
        <Field
          label="Capacity (Jumpers)"
          invalid={!!errors.capacity}
          errorText={errors.capacity?.message}
        >
          <Input
            type="number"
            min={1}
            max={50}
            {...register("capacity", {
              required: "Capacity is required",
              valueAsNumber: true,
              min: { value: 1, message: "Must be at least 1" },
              max: { value: 50, message: "Must be at most 50" },
            })}
          />
        </Field>

        {/* Active Status */}
        <Controller
          control={control}
          name="is_active"
          render={({ field }) => (
            <Field disabled={field.disabled} colorPalette="teal">
              <Checkbox
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked)}
              >
                Active Aircraft
              </Checkbox>
            </Field>
          )}
        />

        {/* Action Buttons */}
        <HStack gap={3} pt={4}>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="submit"
            colorScheme="blue"
            loading={isSubmitting}
            loadingText={aircraft ? "Updating..." : "Creating..."}
          >
            {aircraft ? "Update Aircraft" : "Add Aircraft"}
          </Button>
        </HStack>
      </VStack>
    </form>
  )
}
