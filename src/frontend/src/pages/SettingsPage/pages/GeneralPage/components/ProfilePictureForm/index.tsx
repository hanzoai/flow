import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  type ProfilePicturesQueryResponse,
  useGetProfilePicturesQuery,
} from "@/controllers/API/queries/files";
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@hanzo/ui";
import { gradients } from "../../../../../../utils/styleUtils";
import ProfilePictureChooserComponent from "./components/profilePictureChooserComponent";

type ProfilePictureFormComponentProps = {
  profilePicture: string;
  handleInput: (event: any) => void;
  handlePatchProfilePicture: (gradient: string) => void;
  handleGetProfilePictures: UseQueryResult<ProfilePicturesQueryResponse>;
  userData: any;
};
const ProfilePictureFormComponent = ({
  profilePicture,
  handleInput,
  handlePatchProfilePicture,
  handleGetProfilePictures,
  userData,
}: ProfilePictureFormComponentProps) => {
  const { t } = useTranslation();
  const { isLoading, data, isFetching } = useGetProfilePicturesQuery();

  return (
    <form
      onSubmit={(event) => {
        handlePatchProfilePicture(profilePicture);
        event.preventDefault();
      }}
    >
      <Card x-chunk="dashboard-04-chunk-1">
        <CardHeader>
          <CardTitle>{t("settings.profilePictureTitle")}</CardTitle>
          <CardDescription>
            {t("settings.profilePictureDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-2">
            <ProfilePictureChooserComponent
              profilePictures={data}
              loading={isLoading || isFetching}
              value={
                profilePicture == ""
                  ? (userData?.profile_image ??
                    gradients[
                      parseInt(userData?.id ?? "", 30) % gradients.length
                    ])
                  : profilePicture
              }
              onChange={(value) => {
                handleInput({ target: { name: "profilePicture", value } });
              }}
            />
          </div>
        </CardContent>
        <CardFooter className="border-t px-6 py-4">
          <>
            <Button type="submit">{t("settings.saveButton")}</Button>
          </>
        </CardFooter>
      </Card>
    </form>
  );
};
export default ProfilePictureFormComponent;
