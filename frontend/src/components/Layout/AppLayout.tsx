import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Dropdown, Modal } from 'antd';
import {
  MessageOutlined,
  DatabaseOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MoonOutlined,
  SunOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../store/authStore';
import { useSessionStore } from '../../store/sessionStore';
import { Sidebar } from './Sidebar';

const { Header, Sider, Content } = Layout;

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuthStore();
  const { createSession } = useSessionStore();
  const { token: themeToken } = theme.useToken();

  const handleLogout = () => {
    Modal.confirm({
      title: '确认退出',
      content: '确定要退出登录吗？',
      onOk: () => {
        logout();
        navigate('/login');
      },
    });
  };

  const handleNewChat = async () => {
    const session = await createSession();
    if (session) {
      navigate(`/chat/${session.id}`);
    }
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'profile') navigate('/profile');
    if (key === 'logout') handleLogout();
  };

  const navItems = [
    { key: '/chat', icon: <MessageOutlined />, label: '问答对话' },
    ...(isAdmin() ? [{ key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库管理' }] : []),
  ];

  const selectedKey = location.pathname.startsWith('/knowledge') ? '/knowledge' : '/chat';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={280}
        style={{
          background: themeToken.colorBgContainer,
          borderRight: `1px solid ${themeToken.colorBorderSecondary}`,
        }}
      >
        <div style={{ padding: '16px', borderBottom: `1px solid ${themeToken.colorBorderSecondary}` }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleNewChat}
            style={{ borderRadius: 8 }}
          >
            {!collapsed && '新建对话'}
          </Button>
        </div>
        <Sidebar collapsed={collapsed} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: themeToken.colorBgContainer,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
            height: 56,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
            <Menu
              mode="horizontal"
              selectedKeys={[selectedKey]}
              items={navItems}
              onClick={({ key }) => navigate(key)}
              style={{ border: 'none', background: 'transparent', flex: 1 }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={darkMode ? <SunOutlined /> : <MoonOutlined />}
              onClick={() => setDarkMode(!darkMode)}
            />
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }}>
              <Button type="text" icon={<UserOutlined />}>
                {user?.username}
              </Button>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ padding: 0, background: themeToken.colorBgLayout, height: 'calc(100vh - 56px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}