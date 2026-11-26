import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App"
import { api } from "@/api/client"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { DashboardProvider } from "@/context/dashboard"
import { type Meta, initDict } from "@/data/dict"

// 先拉元数据（DA 字典、数据截至日、角色）再渲染，保证各处读到初始化后的字典常量
api<Meta>("/insight/meta")
  .then(initDict)
  .then(() => {
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <TooltipProvider>
          <DashboardProvider>
            <App />
            <Toaster position="top-center" />
          </DashboardProvider>
        </TooltipProvider>
      </StrictMode>
    )
  })
  .catch((e: Error) => {
    document.getElementById("root")!.innerText = `后端不可用：${e.message}（请先启动后端 8420 端口）`
  })
