import { Geist, Geist_Mono } from "next/font/google";
import Header from "@/components/Header";
import Scene3D from "@/components/Scene3D";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata = {
  title: "DevAscend – Developer Growth Predictor",
  description: "Predict your developer level, growth curve, time to goal and learning roadmap.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <Scene3D />
        <Header />
        {children}
      </body>
    </html>
  );
}
