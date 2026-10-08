// ESLint (flat config) del frontend de TexCore. Reemplaza al `eslintConfig: react-app`
// heredado de Create React App, que no tenía dependencias instaladas ni se ejecutaba.
// Plan: docs/superpowers/plans/2026-10-05-modernizacion-ci-cd.md (Fase 2).
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Quitar claves con desestructuración y resto (`const { a, ...resto } = x`) es el modo
      // idiomático de omitir campos; la variable descartada no es código muerto.
      '@typescript-eslint/no-unused-vars': ['error', { ignoreRestSiblings: true }],
    },
  },
);
