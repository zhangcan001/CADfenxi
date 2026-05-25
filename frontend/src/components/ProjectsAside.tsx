import React from "react";

import type { Project } from "../api/projects";
import { formatDate } from "../formatters";

interface ProjectsAsideProps {
  projects: Project[];
  selectedProject: Project | null;
  loadingProjects: boolean;
  projectError: string;
  formError: string;
  name: string;
  description: string;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCreateProject: (event: React.FormEvent<HTMLFormElement>) => void;
  onOpenProject: (id: number) => void;
  onDeleteProject: (id: number) => void;
}

export function ProjectsAside({
  projects,
  selectedProject,
  loadingProjects,
  projectError,
  formError,
  name,
  description,
  onNameChange,
  onDescriptionChange,
  onCreateProject,
  onOpenProject,
  onDeleteProject
}: ProjectsAsideProps) {
  return (
    <aside className="project-list">
      <div className="section-title">
        <h2>最近项目</h2>
        <span>{projects.length} 个项目</span>
      </div>

      <form className="project-form" onSubmit={onCreateProject}>
        <label>
          项目名称
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder="例如：某住宅项目"
          />
        </label>
        <label>
          项目说明
          <textarea
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            placeholder="可填写施工阶段、用途等说明"
            rows={3}
          />
        </label>
        {formError ? <p className="form-error">{formError}</p> : null}
        <button type="submit">新建项目</button>
      </form>

      {projectError ? <p className="form-error">{projectError}</p> : null}

      {loadingProjects ? (
        <p className="empty-state">项目列表加载中...</p>
      ) : projects.length === 0 ? (
        <p className="empty-state">暂无项目，请新建项目。</p>
      ) : (
        <div className="project-cards">
          {projects.map((project) => (
            <article
              className={
                selectedProject?.id === project.id
                  ? "project-card active"
                  : "project-card"
              }
              key={project.id}
            >
              <div>
                <h3>{project.name}</h3>
                <p>{project.description || "暂无项目说明。"}</p>
              </div>
              <dl>
                <div>
                  <dt>图纸总数</dt>
                  <dd>{project.stats.sheet_count}</dd>
                </div>
                <div>
                  <dt>待校核</dt>
                  <dd>{project.stats.need_review_count}</dd>
                </div>
                <div>
                  <dt>问题数量</dt>
                  <dd>{project.stats.issue_count}</dd>
                </div>
              </dl>
              <div className="meta">
                <span>最近打开：{formatDate(project.last_opened_at ?? project.updated_at)}</span>
                <span>最近更新：{formatDate(project.updated_at)}</span>
              </div>
              <div className="card-actions">
                <button type="button" onClick={() => onOpenProject(project.id)}>
                  打开项目
                </button>
                <button
                  type="button"
                  className="ghost danger"
                  onClick={() => onDeleteProject(project.id)}
                >
                  删除空项目
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </aside>
  );
}
