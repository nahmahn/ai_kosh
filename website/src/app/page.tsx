import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import Architecture from "@/components/Architecture";
import ImpactStats from "@/components/ImpactStats";
import CTABanner from "@/components/CTABanner";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <Hero />
      <HowItWorks />
      <Architecture />
      <ImpactStats />
      <CTABanner />
      <Footer />
    </>
  );
}
