import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",
  plugins: [
    "@hey-api/typescript",
    "@hey-api/client-axios",
    {
      name: "@hey-api/sdk",
      operations: {
        strategy: "byTags",
        containerName: "{{name}}Service",
        methodName: (name) =>
          name.replace(
            /^(login|users|items|aircraft|instructors|loads|jumps|weather|analytics|utils|private)[-_]?/i,
            "",
          ),
      },
    },
  ],
})
