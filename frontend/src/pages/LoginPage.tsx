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
        : "操作失败，请稍后重试";
      message.error(msg || "操作失败，请稍后重试");
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
          <p style={{ color: "#888", margin: "8px 0 0", fontSize: 18 }}>你的 AI 数据工作台</p>
        </div>
        <Tabs
          centered
          items={[
            {
              key: "login",
              label: "登录",
              children: (
                <Form onFinish={(v) => handleSubmit(v, "login")} layout="vertical">
                  <Form.Item name="email" rules={[{ required: true, type: "email" }]}>
                    <Input prefix={<MailOutlined />} placeholder="邮箱" size="large" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block size="large">
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form onFinish={(v) => handleSubmit(v, "register")} layout="vertical">
                  <Form.Item name="email" rules={[{ required: true, type: "email" }]}>
                    <Input prefix={<MailOutlined />} placeholder="邮箱" size="large" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码（至少 6 位）" size="large" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block size="large">
                    创建账号
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
