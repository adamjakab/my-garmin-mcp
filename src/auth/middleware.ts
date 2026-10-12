import type { RequestHandler } from "express";

export function bearerAuth(verify: (key: string) => boolean): RequestHandler {
  return (req, res, next) => {
    const match = /^Bearer (.+)$/i.exec(req.header("authorization") ?? "");
    if (!match?.[1] || !verify(match[1])) {
      res.status(401).set("WWW-Authenticate", "Bearer").json({
        jsonrpc: "2.0",
        error: { code: -32001, message: "Unauthorized" },
        id: null,
      });
      return;
    }
    next();
  };
}
