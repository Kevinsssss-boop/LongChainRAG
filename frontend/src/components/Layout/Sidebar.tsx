import { useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { List, Button, Popconfirm, Typography, theme } from 'antd';
import { DeleteOutlined, MessageOutlined } from '@ant-design/icons';
import { useSessionStore } from '../../store/sessionStore';
import dayjs from 'dayjs';

const { Text } = Typography;

interface SidebarProps {
  collapsed: boolean;
}

export function Sidebar({ collapsed }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  // Extract sessionId from URL: /chat/:sessionId
  const currentSessionId = useMemo(() => {
    const match = location.pathname.match(/\/chat\/(.+)/);
    return match ? match[1] : null;
  }, [location.pathname]);

  const { sessions, fetchSessions, deleteSession } = useSessionStore();
  const { token: themeToken } = theme.useToken();

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleSelect = (id: string) => {
    navigate(`/chat/${id}`);
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
      <List
        dataSource={sessions}
        locale={{ emptyText: collapsed ? '' : '暂无对话' }}
        renderItem={(item) => (
          <List.Item
            key={item.id}
            onClick={() => handleSelect(item.id)}
            style={{
              cursor: 'pointer',
              padding: collapsed ? '8px 16px' : '8px 16px',
              background: item.id === currentSessionId ? themeToken.colorPrimaryBg : 'transparent',
              border: 'none',
              borderRadius: 8,
              margin: '2px 8px',
              transition: 'background 0.2s',
            }}
            actions={
              !collapsed
                ? [
                    <Popconfirm
                      key="delete"
                      title="确定删除此对话？"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        deleteSession(item.id);
                      }}
                      onCancel={(e) => e?.stopPropagation()}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>,
                  ]
                : []
            }
          >
            <List.Item.Meta
              avatar={!collapsed ? <MessageOutlined style={{ color: themeToken.colorTextSecondary }} /> : <MessageOutlined />}
              title={
                !collapsed ? (
                  <Text ellipsis style={{ maxWidth: 180, fontSize: 14 }}>
                    {item.title}
                  </Text>
                ) : undefined
              }
              description={
                !collapsed
                  ? dayjs(item.updated_at).format('MM-DD HH:mm')
                  : undefined
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
}