import type React from "react";
import { forwardRef } from "react";
import FlowLogo from "@/assets/FlowLogo.svg?react";

export const HanzoIcon = forwardRef<
  SVGSVGElement,
  React.SVGProps<SVGSVGElement>
>((props, ref) => {
  return <FlowLogo ref={ref} {...props} />;
});

HanzoIcon.displayName = "HanzoIcon";
