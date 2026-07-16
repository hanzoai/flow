import { useTranslation } from "react-i18next";

export default function NoDataPdf(): JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
      <div className="chat-alert-box">
        <span>
          📄 <span className="flow-chat-span">{PDFErrorTitle}</span>
        </span>
        <br />
        <div className="flow-chat-desc">
          <span className="flow-chat-desc-span">{PDFLoadError} </span>
        </div>
      </div>
    </div>
  );
}
