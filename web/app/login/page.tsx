import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ForgotPassword } from "./forgot-password";
import { LoginForm } from "./login-form";

export const metadata = { title: "Sign in · TCGP Optimizer" };

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-sm py-10">
      <Card>
        <CardHeader>
          <CardTitle>Owner sign-in</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Browsing is open to everyone. Sign in to run a sync.
          </p>
          <LoginForm />
          <ForgotPassword />
        </CardContent>
      </Card>
    </div>
  );
}
