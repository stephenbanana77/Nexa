import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Card, Tabs, message } from "antd";
import { MailOutlined, LockOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (values: { email: string; password: string }, mode: "login" | "register") => {
    setLoading(true);
    try {
      if (mode === "login") {
        await login(values.email, values.password);
      } else {
        await register(values.email, values.password);
      }
      navigate("/");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Something went wrong";
      message.error(msg || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0d0d0d",
      }}
    >
      <Card
        style={{ width: "100%", maxWidth: 420, background: "#1a1a1a", border: "1px solid #333" }}
        styles={{ body: { padding: 32 } }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: "#fff", margin: 0 }}>Nexa</h1>
          <p style={{ color: "#888", margin: "8px 0 0", fontSize: 18 }}>Your AI Data Analyst</p>
        </div>
        <Tabs
          centered
          items={[
            {
              key: "login",
              label: "Sign In",
              children: (
                <Form onFinish={(v) => handleSubmit(v, "login")} layout="vertical">
                  <Form.Item name="email" rules={[{ required: true, type: "email" }]}>
                    <Input prefix={<MailOutlined />} placeholder="Email" size="large" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block size="large">
                    Sign In
                  </Button>
                </Form>
              ),
            },
            {
              key: "register",
              label: "Register",
              children: (
                <Form onFinish={(v) => handleSubmit(v, "register")} layout="vertical">
                  <Form.Item name="email" rules={[{ required: true, type: "email" }]}>
                    <Input prefix={<MailOutlined />} placeholder="Email" size="large" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block size="large">
                    Create Account
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
