import { FlatCompat } from "@eslint/eslintrc";
import tseslint from 'typescript-eslint';

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
});

export default tseslint.config(
  {
		ignores: ['.next', 'src/generated']
	},
  ...compat.extends("next/core-web-vitals"),
  {
    files: ['**/*.ts', '**/*.tsx'],
		extends: [
			...tseslint.configs.recommended,
			...tseslint.configs.recommendedTypeChecked,
			...tseslint.configs.stylisticTypeChecked
		],
      rules: {
    "@typescript-eslint/array-type": "off",
    "@typescript-eslint/consistent-type-definitions": "off",
    "@typescript-eslint/consistent-type-imports": [
      "warn",
      { prefer: "type-imports", fixStyle: "inline-type-imports" },
    ],
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/require-await": "off",
    "@typescript-eslint/no-misused-promises": [
      "error",
      { checksVoidReturn: { attributes: false } },
    ],
  },
  },
  {
		linterOptions: {
			reportUnusedDisableDirectives: true
		},
		languageOptions: {
			parserOptions: {
				projectService: true
			}
		}
	},
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/lib/api/client.ts'],
    rules: {
      // `client.ts` is the single fetch door (AGENTS.md §11). Everything else
      // must go through it so auth, base URL and error handling stay in one place.
      'no-restricted-syntax': [
        'error',
        {
          selector: 'CallExpression[callee.name="fetch"]',
          message:
            'Call fetch only from src/lib/api/client.ts — use the typed API client instead.',
        },
      ],
    },
  },
  {
    files: ['**/__tests__/**/*.ts'],
    rules: {
      // node:test registers describe/it; it is not awaited by design.
      '@typescript-eslint/no-floating-promises': 'off',
    },
  },
)
