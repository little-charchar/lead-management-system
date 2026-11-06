"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { setApiPersona, type UserRole } from "@/lib/api";

export interface Persona {
  email: string;
  name: string;
  role: UserRole;
  organization: string;
  initials: string;
}

export const PERSONAS: Persona[] = [
  {
    email: "jane@plaintiff.com",
    name: "Jane Doe",
    role: "PLAINTIFF",
    organization: "Plaintiff",
    initials: "JD",
  },
  {
    email: "sarah@apexlegal.com",
    name: "Sarah Attorney",
    role: "ATTORNEY",
    organization: "Apex Legal Partners",
    initials: "SA",
  },
  {
    email: "david@beaconrights.com",
    name: "David Attorney",
    role: "ATTORNEY",
    organization: "Beacon Rights Group",
    initials: "DA",
  },
  {
    email: "admin@system.com",
    name: "Elena Admin",
    role: "ADMIN",
    organization: "System Administrator",
    initials: "EA",
  },
];

interface AuthContextValue {
  persona: Persona;
  setPersonaEmail: (email: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>(PERSONAS[0]);

  const setPersonaEmail = useCallback((email: string) => {
    const selected = PERSONAS.find((item) => item.email === email);
    if (!selected) return;
    setPersona(selected);
    setApiPersona(selected.email);
  }, []);

  const value = useMemo(
    () => ({ persona, setPersonaEmail }),
    [persona, setPersonaEmail],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
}
