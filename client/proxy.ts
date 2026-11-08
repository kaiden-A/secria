import { NextResponse, type NextRequest } from "next/server";

// UX only: the real authorization is always server-side. Keep this cookie name
// in sync with SECRIA_SESSION_COOKIE_NAME.
const SESSION_COOKIE = "secria_session";

const PROTECTED = ["/w", "/settings"];

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const session = req.cookies.get(SESSION_COOKIE)?.value;

  const guarded = PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!guarded) return NextResponse.next();
  if (session) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!api|_next|assets|favicon|icon|.*\\..*).*)"],
};
