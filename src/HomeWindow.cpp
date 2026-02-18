#include "HomeWindow.h"

#include <QButtonGroup>
#include <QDir>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QStandardPaths>
#include <QVBoxLayout>
#include <QWidget>

HomeWindow::HomeWindow(QWidget *parent)
    : QMainWindow(parent) {
  setupUi();
  applyStyles();
}

void HomeWindow::setupUi() {
  auto *central = new QWidget(this);
  setCentralWidget(central);
  resize(980, 680);
  setMinimumSize(840, 560);
  setWindowTitle("SlideApp");

  auto *root = new QVBoxLayout(central);
  root->setContentsMargins(70, 30, 70, 40);
  root->setSpacing(0);

  auto *topRow = new QHBoxLayout();
  topRow->addStretch();

  researcherButton_ = new QPushButton("Researcher Mode", this);
  researcherButton_->setCheckable(true);

  adminButton_ = new QPushButton("Admin Mode", this);
  adminButton_->setCheckable(true);

  auto *modeGroup = new QButtonGroup(this);
  modeGroup->setExclusive(true);
  modeGroup->addButton(researcherButton_);
  modeGroup->addButton(adminButton_);

  topRow->addWidget(researcherButton_);
  topRow->addSpacing(10);
  topRow->addWidget(adminButton_);
  root->addLayout(topRow);

  root->addSpacing(86);

  auto *title = new QLabel("Emerson Lab", this);
  title->setAlignment(Qt::AlignHCenter);
  title->setObjectName("titleLabel");
  root->addWidget(title);

  root->addSpacing(44);

  auto *formWrap = new QWidget(this);
  formWrap->setMaximumWidth(760);
  auto *form = new QVBoxLayout(formWrap);
  form->setContentsMargins(0, 0, 0, 0);
  form->setSpacing(18);

  auto *userRow = new QHBoxLayout();
  userRow->setSpacing(14);
  auto *userLabel = new QLabel("User:", this);
  userLabel->setObjectName("fieldLabel");
  userEdit_ = new QLineEdit(this);
  userEdit_->setObjectName("fieldInput");
  userEdit_->setMinimumWidth(420);
  userEdit_->setPlaceholderText("");
  userRow->addWidget(userLabel);
  userRow->addWidget(userEdit_, 1);
  form->addLayout(userRow);

  auto *outputRow = new QHBoxLayout();
  outputRow->setSpacing(14);
  auto *outputLabel = new QLabel("Output Directory (Optional):", this);
  outputLabel->setObjectName("fieldLabel");
  outputDirEdit_ = new QLineEdit(this);
  outputDirEdit_->setObjectName("fieldInput");
  outputDirEdit_->setMinimumWidth(420);
  outputDirEdit_->setPlaceholderText("");

  QString downloads = QStandardPaths::writableLocation(QStandardPaths::DownloadLocation);
  if (downloads.isEmpty()) {
    downloads = QDir::homePath() + "/Downloads";
  }
  outputDirEdit_->setText(downloads);

  outputRow->addWidget(outputLabel);
  outputRow->addWidget(outputDirEdit_, 1);
  form->addLayout(outputRow);

  auto *formCenterRow = new QHBoxLayout();
  formCenterRow->addStretch();
  formCenterRow->addWidget(formWrap);
  formCenterRow->addStretch();
  root->addLayout(formCenterRow);

  root->addSpacing(64);

  beginButton_ = new QPushButton("Begin", this);
  beginButton_->setObjectName("beginButton");
  beginButton_->setFixedSize(210, 74);

  auto *beginRow = new QHBoxLayout();
  beginRow->addStretch();
  beginRow->addWidget(beginButton_);
  beginRow->addStretch();
  root->addLayout(beginRow);

  root->addStretch();

  researcherButton_->setChecked(true);
  setModeResearcher();

  connect(researcherButton_, &QPushButton::clicked, this, &HomeWindow::setModeResearcher);
  connect(adminButton_, &QPushButton::clicked, this, &HomeWindow::setModeAdmin);
}

void HomeWindow::applyStyles() {
  setStyleSheet(
      "QMainWindow { background: #000000; }"
      "QWidget { color: #f2f2f2; font-family: 'Helvetica Neue'; }"
      "QLabel#titleLabel { font-size: 78px; font-weight: 300; letter-spacing: 1px; }"
      "QLabel#fieldLabel { font-size: 42px; font-weight: 400; }"
      "QLineEdit#fieldInput {"
      "  background: transparent;"
      "  border: none;"
      "  color: #ffffff;"
      "  font-size: 42px;"
      "  font-weight: 400;"
      "  padding: 0;"
      "}"
      "QPushButton {"
      "  background: #d9d9d9;"
      "  color: #111111;"
      "  border: none;"
      "  border-radius: 11px;"
      "  padding: 10px 18px;"
      "  font-size: 25px;"
      "}"
      "QPushButton:hover { background: #ececec; }"
      "QPushButton:pressed { background: #bbbbbb; }"
      "QPushButton#beginButton {"
      "  background: #84F28A;"
      "  color: #000000;"
      "  border-radius: 36px;"
      "  font-size: 58px;"
      "  font-weight: 500;"
      "  padding-bottom: 8px;"
      "}"
      "QPushButton#beginButton:hover { background: #95f69a; }"
      "QPushButton#beginButton:pressed { background: #76e87d; }");
}

void HomeWindow::setModeResearcher() {
  researcherButton_->setChecked(true);

  researcherButton_->setStyleSheet(
      "QPushButton {"
      "  background: #84F28A;"
      "  color: #000000;"
      "  border: none;"
      "  border-radius: 11px;"
      "  padding: 10px 18px;"
      "  font-size: 25px;"
      "}");

  adminButton_->setStyleSheet(
      "QPushButton {"
      "  background: #d9d9d9;"
      "  color: #111111;"
      "  border: none;"
      "  border-radius: 11px;"
      "  padding: 10px 18px;"
      "  font-size: 25px;"
      "}");
}

void HomeWindow::setModeAdmin() {
  adminButton_->setChecked(true);

  adminButton_->setStyleSheet(
      "QPushButton {"
      "  background: #F26565;"
      "  color: #000000;"
      "  border: none;"
      "  border-radius: 11px;"
      "  padding: 10px 18px;"
      "  font-size: 25px;"
      "}");

  researcherButton_->setStyleSheet(
      "QPushButton {"
      "  background: #d9d9d9;"
      "  color: #111111;"
      "  border: none;"
      "  border-radius: 11px;"
      "  padding: 10px 18px;"
      "  font-size: 25px;"
      "}");
}
