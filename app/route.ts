import html from "./ranking-html";
import { htmlResponse } from "../lib/security-headers";
export function GET(){return htmlResponse(html)}
