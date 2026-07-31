import { Button, Result } from "antd";
import { useNavigate } from "react-router-dom";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0d0d0d",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}>
      <Result
        status="404"
        title="Page Not Found"
        subTitle="The page you're looking for doesn't exist or has been moved."
        extra={
          <Button type="primary" onClick={() => navigate("/")}>
            Back to Home
          </Button>
        }
      />
    </div>
  );
}
