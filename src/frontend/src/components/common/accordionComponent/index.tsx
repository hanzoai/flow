import { useState } from "react";
import type { AccordionComponentType } from "@/types/components";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@hanzo/ui";

export default function AccordionComponent({
  trigger,
  children,
  disabled,
  open = [],
  keyValue,
}: AccordionComponentType): JSX.Element {
  const [expanded, setExpanded] = useState(
    open.length === 0 ? false : open.includes(keyValue ?? ""),
  );

  return (
    <Collapsible
      open={expanded}
      onOpenChange={(next: boolean) => {
        if (!disabled) setExpanded(next);
      }}
    >
      <CollapsibleTrigger className="w-full">{trigger}</CollapsibleTrigger>
      <CollapsibleContent>
        <div className="AccordionContent flex flex-col">{children}</div>
      </CollapsibleContent>
    </Collapsible>
  );
}
