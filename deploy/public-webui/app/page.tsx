import type { Metadata } from "next";
import { PublicDemoConsole } from "./PublicDemoConsole";

export const metadata: Metadata = {
  title: "PyRepair Agent Public Demo",
  description: "A mock-only public console for inspecting PyRepair Agent runs.",
};

export default function Home() {
  return <PublicDemoConsole />;
}
