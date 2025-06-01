import {
  Checkbox as ChakraUICheckbox,
  type UseCheckboxProps as ChakraUICheckboxProps,
} from "@chakra-ui/react"
import * as React from "react"

// Define custom props, extending relevant ChakraUICheckboxProps
// Omit props that will be handled explicitly or differently (isChecked, onChange, icon, onCheckedChange)
export interface CheckboxProps
  extends Omit<
    ChakraUICheckboxProps,
    "isChecked" | "onChange" | "icon" | "onCheckedChange"
  > {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  icon?: React.ElementType // Use ElementType for Chakra's icon prop
  children?: React.ReactNode
}

export const Checkbox = React.forwardRef<HTMLLabelElement, CheckboxProps>(
  function Checkbox(props, ref) {
    const {
      checked,
      onCheckedChange,
      children,
      icon: customIcon,
      ...rest
    } = props

    return (
      <ChakraUICheckbox.Root
        ref={ref}
        checked={checked}
        // onCheckedChange={handleChange}
        // icon={customIcon ? <Icon as={customIcon} /> : undefined}
        {...rest}
      >
        {children}
      </ChakraUICheckbox.Root>
    )
  },
)
