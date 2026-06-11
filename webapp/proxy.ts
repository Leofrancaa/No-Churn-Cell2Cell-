import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";

const SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET ?? "dev-secret-trocar-no-deploy",
);

export async function proxy(req: NextRequest) {
  const token = req.cookies.get("session")?.value;
  const loginUrl = new URL("/login", req.url);
  if (!token) {
    return NextResponse.redirect(loginUrl);
  }
  try {
    await jwtVerify(token, SECRET, { algorithms: ["HS256"] });
    return NextResponse.next();
  } catch {
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: ["/((?!login|api|_next/static|_next/image|favicon.ico).*)"],
};
