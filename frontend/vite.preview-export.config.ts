import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

/**
 * 用于导出「可发给业务确认」的单文件 HTML：
 * 真实 React/recharts 运行时打包进同一个 html，抽屉、图表 hover 等交互都是真实的，
 * 不依赖开发服务器，双击即可在浏览器里打开。不用于日常开发/线上构建。
 */
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss(), viteSingleFile()],
  resolve: {
    alias: {
      '@/assets/figma/ai-illustration.png': path.resolve(
        __dirname,
        './src/assets/figma/preview-export/ai-illustration.png'
      ),
      '@/assets/figma/avatar.png': path.resolve(
        __dirname,
        './src/assets/figma/preview-export/avatar.png'
      ),
      '@': path.resolve(__dirname, './src'),
      // 自托管中文变量字体会被拆成近百个 unicode-range 子集，inline 后几 MB，
      // 预览导出不需要这种程度的字体保真，替换成空样式，回退系统默认中文字体
      '@fontsource-variable/noto-sans-sc': path.resolve(
        __dirname,
        './src/assets/preview-export-empty.css'
      ),
    },
  },
  build: {
    outDir: 'dist-preview',
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
  },
})
