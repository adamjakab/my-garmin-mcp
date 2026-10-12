import type { RequestHandler } from "express";
import type { KeyStore } from "./keystore.js";

export function bearerAuth(keys: KeyStore): RequestHandler {
  return (req, res, next) => {
    const match = /^Bearer (.+)$/i.exec(req.header("authorization") ?? "");
    if (!match?.[1] || !keys.verify(match[1])) {
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
