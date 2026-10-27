/** Backend origin. Empty = same origin (Vite dev proxy / reverse proxy in prod). */
export const API_BASE: string = import.meta.env.VITE_API_URL ?? ""
