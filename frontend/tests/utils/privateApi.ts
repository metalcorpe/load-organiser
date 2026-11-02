// Note: the `PrivateService` is only available when generating the client
// for local environments
import { PrivateService } from "../../src/client"
import { client } from "../../src/client/client.gen"

client.setConfig({ baseURL: process.env.VITE_API_URL, throwOnError: true })

export const createUser = async ({
  email,
  password,
}: {
  email: string
  password: string
}) => {
  const { data } = await PrivateService.createUser({
    throwOnError: true,
    body: {
      email,
      password,
      full_name: "Test User",
    },
  })
  return data
}
