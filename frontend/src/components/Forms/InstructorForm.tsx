import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect } from "react"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { Button, Heading, Input, Text, VStack } from "@chakra-ui/react" // Added Input

import { type InstructorPublic, InstructorsService } from "../../client"
import useCustomToast from "../../hooks/useCustomToast"
import { Checkbox } from "../ui/checkbox"
import { Field } from "../ui/field"

// Define the Zod schema based on InstructorPublic fields
const instructorSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email address"),
  tandem_certified: z.boolean().optional(),
  aff_certified: z.boolean().optional(),
  is_active: z.boolean().optional(),
})

// Generate the TypeScript type from the Zod schema
type InstructorFormData = z.infer<typeof instructorSchema>

interface InstructorFormProps {
  type: "create" | "update"
  instructor?: InstructorPublic | null
  onSuccess?: () => void
}

const InstructorForm = ({
  type,
  instructor,
  onSuccess,
}: InstructorFormProps) => {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InstructorFormData>({
    resolver: zodResolver(instructorSchema),
    defaultValues: {
      name: "",
      email: "",
      tandem_certified: false,
      aff_certified: false,
      is_active: true,
    },
  })

  useEffect(() => {
    if (instructor) {
      reset({
        name: instructor.name,
        email: instructor.email,
        tandem_certified: instructor.tandem_certified || false,
        aff_certified: instructor.aff_certified || false,
        is_active:
          instructor.is_active === undefined ? true : instructor.is_active,
      })
    } else {
      reset({
        name: "",
        email: "",
        tandem_certified: false,
        aff_certified: false,
        is_active: true,
      })
    }
  }, [instructor, reset])

  const onSubmit = async (data: InstructorFormData) => {
    try {
      if (type === "create") {
        await InstructorsService.createInstructor({
          requestBody: {
            name: data.name,
            email: data.email,
            tandem_certified: data.tandem_certified,
            aff_certified: data.aff_certified,
            is_active: data.is_active,
          },
        })
        showSuccessToast("Instructor created successfully.")
      } else if (type === "update" && instructor) {
        await InstructorsService.updateInstructor({
          id: instructor.id,
          requestBody: {
            name: data.name,
            email: data.email,
            tandem_certified: data.tandem_certified,
            aff_certified: data.aff_certified,
            is_active: data.is_active,
          },
        })
        showSuccessToast("Instructor updated successfully.")
      }
      if (onSuccess) {
        onSuccess()
      }
    } catch (err) {
      showErrorToast(
        `Error ${type === "create" ? "creating" : "updating"} instructor.`,
      )
      console.error(err)
    }
  }

  return (
    <VStack as="form" onSubmit={handleSubmit(onSubmit)} gap={4} w="100%">
      {" "}
      {/* spacing changed to gap */}
      <Heading size="md" mb={4} alignSelf="flex-start">
        {type === "create" ? "Create New Instructor" : "Edit Instructor"}
      </Heading>
      <Field label="Name" errorText={errors.name?.message}>
        {" "}
        {/* Changed error to errorText and passed message */}
        <Controller
          name="name"
          control={control}
          render={({ field }) => <Input {...field} />}
        />
      </Field>
      <Field label="Email" errorText={errors.email?.message}>
        {" "}
        {/* Changed error to errorText and passed message */}
        <Controller
          name="email"
          control={control}
          render={({ field }) => <Input {...field} type="email" />}
        />
      </Field>
      <Controller
        name="tandem_certified"
        control={control}
        render={({ field }) => (
          <Checkbox checked={field.value} onCheckedChange={field.onChange}>
            Tandem Certified
          </Checkbox>
        )}
      />
      {errors.tandem_certified && (
        <Text color="red.500">{errors.tandem_certified.message}</Text>
      )}
      <Controller
        name="aff_certified"
        control={control}
        render={({ field }) => (
          <Checkbox checked={field.value} onCheckedChange={field.onChange}>
            AFF Certified
          </Checkbox>
        )}
      />
      {errors.aff_certified && (
        <Text color="red.500">{errors.aff_certified.message}</Text>
      )}
      <Controller
        name="is_active"
        control={control}
        render={({ field }) => (
          <Checkbox checked={field.value} onCheckedChange={field.onChange}>
            Active
          </Checkbox>
        )}
      />
      {errors.is_active && (
        <Text color="red.500">{errors.is_active.message}</Text>
      )}
      <Button
        type="submit"
        colorScheme="blue"
        loading={isSubmitting} // isLoading to loading
        w="100%"
        mt={6}
      >
        {type === "create" ? "Create Instructor" : "Save Changes"}
      </Button>
    </VStack>
  )
}

export default InstructorForm
