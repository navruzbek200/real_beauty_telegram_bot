import js from '@eslint/js'
import boundaries from 'eslint-plugin-boundaries'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

// Feature-Sliced Design layers, high to low. A slice may only import from its
// own layer's public API (index.ts) or from a strictly lower layer — never
// sideways within the same layer, never upward.
const LAYERS = ['app', 'pages', 'widgets', 'features', 'entities', 'shared']

// app and shared are technical layers (providers/router/styles,
// api/ui/lib/config) — their sub-folders are segments, not business slices,
// so they may freely reference each other. Everything else is a real slice:
// same-layer imports are only allowed within the same slice (its own public
// API), matching "cross-imports between slices on the same layer are
// forbidden".
const TECHNICAL_LAYERS = new Set(['app', 'shared'])

const policies = LAYERS.flatMap((layer, index) => {
  const lowerTypes = LAYERS.slice(index + 1)
  const from = { element: { type: layer } }

  const sameLayerPolicy = TECHNICAL_LAYERS.has(layer)
    ? { from, allow: { to: { element: { type: layer } } } }
    : {
        from,
        allow: {
          to: { element: { type: layer, captured: { slice: '{{from.slice}}' } } },
        },
      }

  const policiesForLayer = [sameLayerPolicy]
  if (lowerTypes.length > 0) {
    policiesForLayer.push({
      from,
      allow: { to: { element: { types: { anyOf: lowerTypes } } } },
    })
  }
  return policiesForLayer
})

export default tseslint.config(
  { ignores: ['dist', 'src/shared/api/generated.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      boundaries,
    },
    settings: {
      'import/resolver': {
        typescript: { project: './tsconfig.app.json' },
      },
      'boundaries/elements': LAYERS.map((layer) => ({
        type: layer,
        pattern: `src/${layer}/*`,
        capture: ['slice'],
      })),
      'boundaries/include': ['src/**/*'],
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'boundaries/dependencies': ['error', { default: 'disallow', policies }],
    },
  },
)
