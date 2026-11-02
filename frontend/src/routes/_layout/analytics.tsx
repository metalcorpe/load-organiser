import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/analytics")({
  component: () => <p>Analytics are not available yet.</p>,
})
