import api from "./api";

export async function apiFetch(
  url: string,
  options: RequestInit = {}
) {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;


  let response = await fetch(
    `${api.defaults.baseURL}${url}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),
        ...options.headers,
      },
      credentials: "include",
    }
  );


  if (response.status === 401) {
    // gọi refresh giống api.ts
    await api.post("/auth/token/refresh");


    const newToken =
      localStorage.getItem("access_token");


    response = await fetch(
      `${api.defaults.baseURL}${url}`,
      {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(newToken
            ? {
                Authorization:
                  `Bearer ${newToken}`,
              }
            : {}),
          ...options.headers,
        },
        credentials: "include",
      }
    );
  }


  return response;
}