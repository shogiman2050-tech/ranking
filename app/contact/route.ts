import html from "./content";
import { htmlResponse } from "../../lib/security-headers";
export function GET(){return htmlResponse(html)}
