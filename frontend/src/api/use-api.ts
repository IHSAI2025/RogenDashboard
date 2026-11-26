import * as React from "react"

import { type Params, api } from "./client"

export interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/** 以 path+params 的 JSON 作为依赖请求；path 为 null 时不请求。切换参数期间保留上一次的 data（避免闪烁），loading 为 true。 */
export function useApi<T = any>(path: string | null, params: Params = {}): ApiState<T> {
  const key = `${path}?${JSON.stringify(params)}`
  const [state, setState] = React.useState<ApiState<T>>({ data: null, loading: !!path, error: null })
  React.useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null })
      return
    }
    let off = false
    setState((s) => ({ ...s, loading: true, error: null }))
    api<T>(path, params)
      .then((data) => !off && setState({ data, loading: false, error: null }))
      .catch((e: Error) => !off && setState((s) => ({ ...s, loading: false, error: e.message })))
    return () => {
      off = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return state
}
