import { useState } from "react";
import { Modal, Form, Input, InputNumber, Button, message } from "antd";
import { DatabaseOutlined } from "@ant-design/icons";
import api from "../api/client";

interface Props {
  projectId: string;
  open: boolean;
  onClose: () => void;
  onConnected: (data: any) => void;
}

export default function MySQLConnectModal({ projectId, open, onClose, onConnected }: Props) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleConnect = async (values: any) => {
    setLoading(true);
    try {
      const { data } = await api.post("/api/datasets/connect-mysql", {
        project_id: projectId,
        ...values,
      });
      message.success(`已连接 ${values.database}（${data.tables?.length || 0} 张表）`);
      onConnected(data);
      onClose();
      form.resetFields();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "连接失败，请检查地址和凭据后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="连接 MySQL 数据库"
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleConnect}>
        <Form.Item name="host" label="主机地址" rules={[{ required: true }]} initialValue="localhost">
          <Input placeholder="localhost" />
        </Form.Item>
        <Form.Item name="port" label="端口" initialValue={3306}>
          <InputNumber min={1} max={65535} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="user" label="用户名" rules={[{ required: true }]} initialValue="root">
          <Input placeholder="root" />
        </Form.Item>
        <Form.Item name="password" label="密码">
          <Input.Password placeholder="数据库密码" />
        </Form.Item>
        <Form.Item name="database" label="数据库" rules={[{ required: true }]}>
          <Input placeholder="my_database" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block icon={<DatabaseOutlined />}>
          连接并导入
        </Button>
      </Form>
    </Modal>
  );
}
