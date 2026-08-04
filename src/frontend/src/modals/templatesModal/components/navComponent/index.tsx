import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { convertTestName } from "@/components/common/storeCardComponent/utils/convert-test-name";
import { cn } from "@/utils/utils";
import { useIsMobile } from "../../../../hooks/use-mobile";
import type { NavProps } from "../../../../types/templates/types";

export function Nav({ categories, currentTab, setCurrentTab }: NavProps) {
  const isMobile = useIsMobile();

  return (
    <>
      <>
        <div
          className={cn("relative flex items-center gap-2 px-2 py-3 md:px-4")}
          data-testid="modal-title"
        >
          
          <div
            className={cn(
              "text-base-semibold flex h-8 shrink-0 items-center rounded-md leading-none tracking-tight text-primary outline-none ring-ring transition-[margin,opa] duration-200 ease-linear focus-visible:ring-1 [&>svg]:size-4 [&>svg]:shrink-0",
              "group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0",
            )}
          >
            Templates
          </div>
        </div>

        {categories.map((category, index) => (
          <>
            <>
              {category.title}
            </>
            <>
              <>
                {category.items.map((link) => (
                  <>
                    <>
                      <ForwardedIconComponent
                        name={link.icon}
                        className={`h-4 w-4 stroke-2 ${
                          currentTab === link.id
                            ? "text-accent-pink-foreground"
                            : "text-muted-foreground"
                        }`}
                      />
                      <span
                        data-testid={`category_title_${convertTestName(link.title)}`}
                      >
                        {link.title}
                      </span>
                    </>
                  </>
                ))}
              </>
            </>
          </>
        ))}
      </>
    </>
  );
}
