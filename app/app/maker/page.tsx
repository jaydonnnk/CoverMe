import type { Metadata } from "next";
import { DemoWorkspace } from "@/components/demo-workspace";

export const metadata: Metadata = { title: "Maker workspace" };

export default function MakerPage() {
  return <DemoWorkspace view="maker" />;
}
