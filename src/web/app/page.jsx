import FilterBar from "@/app/components/FilterBar";
import Map from "@/app/components/Map";
import Ranking from "@/app/components/Ranking";

export default function Home() {
  return (
    <main>
      <h1>Alerta</h1>
      <FilterBar />
      <Map />
      <Ranking />
    </main>
  );
}
