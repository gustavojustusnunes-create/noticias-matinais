import { getLatestEdition } from "../lib/getEditions";
import { JournalView } from "../components/JournalView";

export const revalidate = 60; // revalidate every minute for new editions

export default function Home() {
  const edition = getLatestEdition();

  return <JournalView edition={edition} />;
}
