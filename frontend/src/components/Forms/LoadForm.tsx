import { Button, HStack, Input, Textarea, VStack } from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"

import {
  type AircraftPublic,
  AircraftService,
  type ApiError,
  type LoadCreate,
  type LoadPublic,
  type LoadStatus,
  type LoadUpdate,
  LoadsService,
} from "../../client"
import useCustomToast from "../../hooks/useCustomToast"
import { Field } from "../ui/field"

const loadStatusEnum = z.enum([
  "planning",
  "confirmed",
  "boarded",
  "departed",
  "completed",
  "cancelled",
])

const loadSchema = z.object({
  aircraft_id: z.string().min(1, "Aircraft is required"),
  scheduled_time: z.string().min(1, "Scheduled time is required"),
  altitude: z
    .number()
    .min(3000, "Must be at least 3,000 ft")
    .max(18000, "Must be at most 18,000 ft")
    .optional(),
  status: loadStatusEnum.optional(),
  notes: z.string().optional(),
})

type LoadFormData = z.infer<typeof loadSchema>

interface LoadFormProps {
  load?: LoadPublic
  onSuccess: () => void
  onCancel: () => void
}

export function LoadForm({ load, onSuccess, onCancel }: LoadFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<LoadFormData>({
    resolver: zodResolver(loadSchema),
    defaultValues: {
      aircraft_id: load?.aircraft_id || "",
      scheduled_time:
        load?.scheduled_time || new Date().toISOString().slice(0, 16),
      altitude: load?.altitude || 10000,
      status: load?.status || "planning",
      notes: load?.notes || "",
    },
  })

  const { data: aircraftList } = useQuery<AircraftPublic[], Error>({
    queryKey: ["aircraft"],
    queryFn: () =>
      AircraftService.readAircraft({}).then((res) =>
        Array.isArray(res) ? res : [],
      ),
  })

  useEffect(() => {
    if (load) {
      reset({
        aircraft_id: load.aircraft_id,
        scheduled_time: load.scheduled_time.slice(0, 16), // Convert to datetime-local format
        altitude: load.altitude,
        status: load.status,
        notes: load.notes || "",
      })
    } else {
      reset({
        aircraft_id: "",
        scheduled_time: new Date().toISOString().slice(0, 16),
        altitude: 10000,
        status: "planning",
        notes: "",
      })
    }
  }, [load, reset])

  const onSubmit = async (data: LoadFormData) => {
    try {
      const loadData = {
        aircraft_id: data.aircraft_id,
        scheduled_time: data.scheduled_time,
        altitude: data.altitude,
        status: data.status as LoadStatus,
        notes: data.notes,
      }

      if (load?.id) {
        await LoadsService.updateLoad({
          id: load.id,
          requestBody: loadData as LoadUpdate,
        })
        showSuccessToast("Load updated successfully")
      } else {
        await LoadsService.createLoad({ requestBody: loadData as LoadCreate })
        showSuccessToast("Load created successfully")
      }

      queryClient.invalidateQueries({ queryKey: ["loads"] })
      onSuccess()
    } catch (error) {
      const err = error as ApiError
      const errDetail = (err.body as { detail?: string | { msg: string }[] })
        ?.detail
      let message = "Something went wrong"
      if (typeof errDetail === "string") {
        message = errDetail
      } else if (
        Array.isArray(errDetail) &&
        errDetail.length > 0 &&
        typeof errDetail[0].msg === "string"
      ) {
        message = errDetail[0].msg
      }
      showErrorToast(message)
    }
  }

  return (
    <VStack
      as="form"
      onSubmit={handleSubmit(onSubmit)}
      gap={4}
      align="stretch"
      w="100%"
    >
      <Field label="Aircraft" errorText={errors.aircraft_id?.message}>
        <Controller
          name="aircraft_id"
          control={control}
          render={({ field }) => (
            <select
              {...field}
              style={{
                width: "100%",
                padding: "8px",
                borderRadius: "6px",
                border: "1px solid #e2e8f0",
              }}
            >
              <option value="">Select aircraft</option>
              {aircraftList?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.registration} - {a.model} (Capacity: {a.capacity})
                </option>
              ))}
            </select>
          )}
        />
      </Field>

      <Field label="Scheduled Time" errorText={errors.scheduled_time?.message}>
        <Input type="datetime-local" {...register("scheduled_time")} />
      </Field>

      <HStack gap={4} w="100%">
        <Field
          label="Altitude (ft)"
          errorText={errors.altitude?.message}
          flex={1}
        >
          <Input
            type="number"
            {...register("altitude", { valueAsNumber: true })}
          />
        </Field>

        <Field label="Status" errorText={errors.status?.message} flex={1}>
          <Controller
            name="status"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                style={{
                  width: "100%",
                  padding: "8px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                }}
              >
                <option value="planning">Planning</option>
                <option value="confirmed">Confirmed</option>
                <option value="boarded">Boarded</option>
                <option value="departed">Departed</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            )}
          />
        </Field>
      </HStack>

      <Field label="Notes" errorText={errors.notes?.message}>
        <Textarea
          placeholder="Additional notes about this load..."
          rows={3}
          {...register("notes")}
        />
      </Field>

      <HStack gap={3} pt={4} justifyContent="flex-end">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" colorScheme="blue" loading={isSubmitting}>
          {load ? "Update Load" : "Create Load"}
        </Button>
      </HStack>
    </VStack>
  )
}
