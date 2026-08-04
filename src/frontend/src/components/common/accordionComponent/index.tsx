import { useState } from "react";
import type { AccordionComponentType } from "@/types/components";
import { cn } from "@/utils/utils";

export default function AccordionComponent({
  trigger,
  children,
  disabled,
  open = [],
  keyValue,
  sideBar,
}: AccordionComponentType): JSX.Element {
  const [value, setValue] = useState(
    open.length === 0 ? "" : getOpenAccordion(),
  );

  function getOpenAccordion(): string {
    let value = "";
    open.forEach((el) => {
      if (el == keyValue) {
        value = keyValue;
      }
    });
    return value;
  }

  function handleClick(): void {
    if (!disabled) {
      value === "" ? setValue(keyValue!) : setValue("");
    }
  }

  return (
    <>
      <>
        <>
          <>
            {trigger}
          </>
          <>
            <div className="AccordionContent flex flex-col">{children}</div>
          </>
        </>
      </>
    </>
  );
}
