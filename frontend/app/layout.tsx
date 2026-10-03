import './globals.css';
import './evidence.css';
import {Workspace} from '@/components/workspace';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'ImpulseTwin AI · HV Engineering', description: 'Physics-guided, inventory-aware impulse generator decision support for POWERnext AI.' };
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body><Workspace>{children}</Workspace></body></html>}
