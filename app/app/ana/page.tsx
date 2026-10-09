import type { Metadata } from "next";
import { DemoWorkspace } from "@/components/demo-workspace";

export const metadata: Metadata = { title: "Shopper workspace" };

export default function ShopperPage() {
  return <DemoWorkspace view="ana" />;
}
