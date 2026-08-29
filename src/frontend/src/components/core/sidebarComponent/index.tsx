import { useLocation } from "react-router-dom";
import { CustomLink } from "@/customization/components/custom-link";
import { cn } from "@/utils/utils";

type SideBarButtonsComponentProps = {
  items: {
    href?: string;
    title: string;
    icon: React.ReactNode;
  }[];
  handleOpenNewFolderModal?: () => void;
};

const SideBarButtonsComponent = ({ items }: SideBarButtonsComponentProps) => {
  const location = useLocation();
  const pathname = location.pathname;

  return (
    <nav className="flex flex-col gap-1 pr-6">
      {items.map((item, index) => (
        <CustomLink key={index} to={item.href!} replace>
          <span
            data-testid={`sidebar-nav-${item.title}`}
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted",
              item.href &&
                pathname.endsWith(item.href) &&
                "bg-muted font-medium",
            )}
          >
            {item.icon}
            <span className="block max-w-full truncate">{item.title}</span>
          </span>
        </CustomLink>
      ))}
    </nav>
  );
};

export default SideBarButtonsComponent;
