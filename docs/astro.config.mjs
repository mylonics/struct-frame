import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Shared Mylonics styles — cloned into docs/mylonics-styles during CI.
// For local dev, clone manually:
//   git clone https://github.com/mylonics/mylonics-styles.git docs/mylonics-styles
import { mylonicsStarlightDefaults } from './mylonics-styles/starlight/config-helpers';

// https://astro.build/config
export default defineConfig({
  site: 'https://struct-frame.mylonics.com',
  integrations: [
    starlight({
      title: 'Struct Frame',
      description:
        'A cross-platform code generation framework for Protocol Buffer serialization. Generate C, C++, TypeScript, Python, and GraphQL code with framing and parsing utilities for structured message communication.',
      logo: {
        src: './src/assets/logo.png',
      },
      favicon: '/favicon.ico',
      ...mylonicsStarlightDefaults('Struct Frame', {
        github: 'https://github.com/mylonics/struct-frame',
        extraCss: ['./src/styles/custom.css'],
        headOptions: {
          ogImage:
            'https://raw.githubusercontent.com/mylonics/struct-frame/main/docs/src/assets/logo.png',
          keywords: [
            'struct frame',
            'protocol buffer',
            'code generation',
            'serialization',
            'C code generator',
            'C++ code generator',
            'TypeScript code generator',
            'Python code generator',
            'GraphQL code generator',
            'embedded systems',
            'message framing',
            'cross-platform communication',
          ],
        },
      }),
      // Override social links with the object format required by Starlight 0.32
      // (mylonics-styles returns an array format which is incompatible)
      social: {
        github: 'https://github.com/mylonics/struct-frame',
      },
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'Quick Start', slug: 'getting-started/quick-start' },
          ],
        },
        {
          label: 'Basic Usage',
          items: [
            {
              label: 'Message Definitions',
              slug: 'basic-usage/message-definitions',
            },
            {
              label: 'Code Generation',
              slug: 'basic-usage/code-generation',
            },
            {
              label: 'Language Examples',
              slug: 'basic-usage/language-examples',
            },
            { label: 'Framing', slug: 'basic-usage/framing' },
            {
              label: 'Framing Details',
              slug: 'basic-usage/framing-details',
            },
          ],
        },
        {
          label: 'Extended Features',
          items: [
            {
              label: 'SDK Overview',
              slug: 'extended-features/sdk-overview',
            },
            { label: 'C++ SDK', slug: 'extended-features/cpp-sdk' },
            {
              label: 'TypeScript/JavaScript SDK',
              slug: 'extended-features/typescript-sdk',
            },
            { label: 'Python SDK', slug: 'extended-features/python-sdk' },
            { label: 'C# SDK', slug: 'extended-features/csharp-sdk' },
            {
              label: 'Advanced Features',
              slug: 'extended-features/custom-features',
            },
          ],
        },
        {
          label: 'Reference',
          items: [
            {
              label: 'Build Integration',
              slug: 'reference/build-integration',
            },
            { label: 'CLI Reference', slug: 'reference/cli-reference' },
            { label: 'Testing', slug: 'reference/testing' },
            { label: 'Development', slug: 'reference/development' },
          ],
        },
      ],
    }),
  ],
});
