import { Nav } from "@/components/Nav";
import { VoiceStage } from "@/components/stage/VoiceStage";

export default function HomePage() {
  return (
    <>
      <Nav active="stage" />
      <VoiceStage />
    </>
  );
}
