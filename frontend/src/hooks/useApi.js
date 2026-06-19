import { useState, useEffect, useCallback } from 'react'

/**
 * Generic data-fetching hook.
 * @param {Function} fetchFn  - async function that returns data
 * @param {Array}    deps     - dependency array (re-fetches when changed)
 * @param {boolean}  skip     - if true, skip initial fetch
 */
export function useApi(fetchFn, deps = [], skip = false) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(!skip)
  const [error, setError] = useState(null)

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFn()
      setData(result)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (!skip) execute()
  }, [execute, skip])

  return { data, loading, error, refetch: execute }
}

/**
 * Mutation hook — for POST/PATCH/DELETE actions.
 * Returns { mutate, loading, error, data }.
 */
export function useMutation(mutateFn) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const mutate = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await mutateFn(...args)
      setData(result)
      return result
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [mutateFn])

  return { mutate, loading, error, data }
}
